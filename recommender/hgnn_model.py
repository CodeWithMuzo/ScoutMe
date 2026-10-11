"""
ScoutMe Heterogeneous Graph Neural Network (HGNN)
=================================================
A PyTorch-based Heterogeneous Graph Neural Network for player scouting,
tactical compatibility estimation, and multi-stakeholder link prediction.

Architecture:
- Type-Specific Input Projection: Projects Player (16), Club (12), Coach (8), Scout (8) into shared d-dim space.
- Relational Message Passing (HeteroGraphConv / Relational GraphSAGE):
  Aggregates contextual neighborhood with degree-normalized relational projections.
- LayerNorm + GELU + Residual connections.
- Output: 64-dimensional L2-normalized dense embeddings for all entities.
- Objective: Bayesian Personalized Ranking (BPR) Link Prediction Loss.
"""

import os
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
from recommender.graph_builder import build_scoutme_graph


def aggregate_messages(src_embeddings, edge_index, num_dst_nodes, rel_weight_matrix):
    """
    Vectorized degree-normalized relational message passing:
    m_{u -> v} = W_r * h_u
    a_v = sum_{u in N(v)} m_{u -> v} / sqrt(deg(v) * deg(u))
    """
    if edge_index.shape[1] == 0:
        return torch.zeros((num_dst_nodes, rel_weight_matrix.out_features),
                           device=src_embeddings.device, dtype=src_embeddings.dtype)

    src_idx = edge_index[0]
    dst_idx = edge_index[1]

    # Project source messages through relation transformation
    projected_src = rel_weight_matrix(src_embeddings[src_idx])

    # Degree normalization
    deg_dst = torch.zeros(num_dst_nodes, device=src_embeddings.device).index_add_(
        0, dst_idx, torch.ones_like(dst_idx, dtype=torch.float32)
    )
    norm = torch.clamp(deg_dst[dst_idx], min=1.0).unsqueeze(-1)
    normalized_messages = projected_src / norm

    # Aggregate into destination nodes
    aggregated = torch.zeros((num_dst_nodes, rel_weight_matrix.out_features),
                             device=src_embeddings.device, dtype=src_embeddings.dtype)
    aggregated.index_add_(0, dst_idx, normalized_messages)
    return aggregated


class ScoutMeHGNNLayer(nn.Module):
    """Single Heterogeneous Graph Convolution Layer with residual connection."""
    def __init__(self, hidden_dim):
        super().__init__()
        self.hidden_dim = hidden_dim

        # Relational message transformations
        self.w_p_c = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Player -> Club
        self.w_c_p = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Club -> Player
        self.w_t_c = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Coach -> Club
        self.w_c_t = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Club -> Coach
        self.w_p_t = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Player -> Coach
        self.w_t_p = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Coach -> Player
        self.w_p_p = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Teammates
        self.w_s_p = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Scout -> Player
        self.w_p_s = nn.Linear(hidden_dim, hidden_dim, bias=False)  # Player -> Scout

        # Self-transformations
        self.self_p = nn.Linear(hidden_dim, hidden_dim)
        self.self_c = nn.Linear(hidden_dim, hidden_dim)
        self.self_t = nn.Linear(hidden_dim, hidden_dim)
        self.self_s = nn.Linear(hidden_dim, hidden_dim)

        # Normalization layers
        self.norm_p = nn.LayerNorm(hidden_dim)
        self.norm_c = nn.LayerNorm(hidden_dim)
        self.norm_t = nn.LayerNorm(hidden_dim)
        self.norm_s = nn.LayerNorm(hidden_dim)

    def forward(self, hp, hc, ht, hs, g):
        num_p = hp.shape[0]
        num_c = hc.shape[0]
        num_t = ht.shape[0]
        num_s = hs.shape[0]

        # 1. Update Player representations
        msg_c2p = aggregate_messages(hc, g['edge_club_player'], num_p, self.w_c_p)
        msg_t2p = aggregate_messages(ht, g['edge_coach_player'], num_p, self.w_t_p)
        msg_p2p = aggregate_messages(hp, g['edge_player_teammate'], num_p, self.w_p_p)
        msg_s2p = aggregate_messages(hs, g['edge_scout_player'], num_p, self.w_s_p)
        agg_p = msg_c2p + msg_t2p + 0.5 * msg_p2p + 0.8 * msg_s2p
        hp_out = self.norm_p(hp + F.gelu(self.self_p(hp) + agg_p))

        # 2. Update Club representations
        msg_p2c = aggregate_messages(hp, g['edge_player_club'], num_c, self.w_p_c)
        msg_t2c = aggregate_messages(ht, g['edge_coach_club'], num_c, self.w_t_c)
        agg_c = msg_p2c + msg_t2c
        hc_out = self.norm_c(hc + F.gelu(self.self_c(hc) + agg_c))

        # 3. Update Coach representations
        msg_c2t = aggregate_messages(hc, g['edge_club_coach'], num_t, self.w_c_t)
        msg_p2t = aggregate_messages(hp, g['edge_player_coach'], num_t, self.w_p_t)
        agg_t = msg_c2t + 0.5 * msg_p2t
        ht_out = self.norm_t(ht + F.gelu(self.self_t(ht) + agg_t))

        # 4. Update Scout representations
        msg_p2s = aggregate_messages(hp, g['edge_player_scout'], num_s, self.w_p_s)
        hs_out = self.norm_s(hs + F.gelu(self.self_s(hs) + msg_p2s))

        return hp_out, hc_out, ht_out, hs_out


class ScoutMeHGNN(nn.Module):
    """
    2-Layer Relational Heterogeneous Graph Neural Network
    for ScoutMe football recommendation and scouting system.
    """
    def __init__(self, hidden_dim=64):
        super().__init__()
        self.hidden_dim = hidden_dim

        # Input dimension projections
        self.proj_p = nn.Sequential(
            nn.Linear(16, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU()
        )
        self.proj_c = nn.Sequential(
            nn.Linear(12, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU()
        )
        self.proj_t = nn.Sequential(
            nn.Linear(8, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU()
        )
        self.proj_s = nn.Sequential(
            nn.Linear(8, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU()
        )

        # 2 Message passing layers
        self.layer1 = ScoutMeHGNNLayer(hidden_dim)
        self.layer2 = ScoutMeHGNNLayer(hidden_dim)

    def forward(self, g):
        # Initial projection
        hp = self.proj_p(g['x_player'])
        hc = self.proj_c(g['x_club'])
        ht = self.proj_t(g['x_coach'])
        hs = self.proj_s(g['x_scout'])

        # Message passing layers
        hp, hc, ht, hs = self.layer1(hp, hc, ht, hs, g)
        hp, hc, ht, hs = self.layer2(hp, hc, ht, hs, g)

        # L2-normalization for cosine similarity
        zp = F.normalize(hp, p=2, dim=-1)
        zc = F.normalize(hc, p=2, dim=-1)
        zt = F.normalize(ht, p=2, dim=-1)
        zs = F.normalize(hs, p=2, dim=-1)

        return zp, zc, zt, zs


def compute_bpr_loss(zp, zc, edge_player_club, num_neg_samples=1):
    """
    Bayesian Personalized Ranking (BPR) Link Prediction Loss:
    L = - sum_{(u, v) in E+, (u, v-) in E-} log sigma( z_u . z_v - z_u . z_v- )
    """
    src_p = edge_player_club[0]
    pos_c = edge_player_club[1]

    # Positive dot products
    pos_scores = (zp[src_p] * zc[pos_c]).sum(dim=-1)

    # Random negative sampling for clubs
    num_clubs = zc.shape[0]
    neg_c = torch.randint(0, num_clubs, (len(src_p),), device=zc.device)
    neg_scores = (zp[src_p] * zc[neg_c]).sum(dim=-1)

    loss = -torch.log(torch.sigmoid(pos_scores - neg_scores) + 1e-8).mean()
    return loss


def train_hgnn(epochs=80, lr=0.005, hidden_dim=64, save_path='data/hgnn_embeddings.pt'):
    """Trains the HGNN model and saves learned embeddings to disk."""
    print(f'[HGNN] Building heterogeneous graph from database...')
    g = build_scoutme_graph()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'[HGNN] Device: {device} | Hidden Dim: {hidden_dim} | Epochs: {epochs}')

    # Move tensors to device
    for k in list(g.keys()):
        if isinstance(g[k], torch.Tensor):
            g[k] = g[k].to(device)

    model = ScoutMeHGNN(hidden_dim=hidden_dim).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    t0 = time.time()
    best_loss = float('inf')

    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()

        zp, zc, zt, zs = model(g)

        # BPR Loss on Player-Club edges
        loss_pc = compute_bpr_loss(zp, zc, g['edge_player_club'])

        # BPR Loss on Player-Coach edges
        loss_pt = compute_bpr_loss(zp, zt, g['edge_player_coach'])

        total_loss = loss_pc + 0.5 * loss_pt
        total_loss.backward()
        optimizer.step()

        if total_loss.item() < best_loss:
            best_loss = total_loss.item()

        if epoch % 10 == 0 or epoch == 1:
            print(f'  Epoch {epoch:02d}/{epochs:02d} | Total Loss: {total_loss.item():.4f} (PC: {loss_pc.item():.4f}, PT: {loss_pt.item():.4f})')

    total_time = time.time() - t0
    print(f'[HGNN] Training completed in {total_time:.2f}s! Best Loss: {best_loss:.4f}')

    # Generate final embeddings
    model.eval()
    with torch.no_grad():
        zp, zc, zt, zs = model(g)

    # Save to disk
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    checkpoint = {
        'zp': zp.cpu(),
        'zc': zc.cpu(),
        'zt': zt.cpu(),
        'zs': zs.cpu(),
        'hidden_dim': hidden_dim,
        'player_metadata': g['player_metadata'],
        'club_metadata': g['club_metadata'],
        'coach_metadata': g['coach_metadata'],
        'scout_metadata': g['scout_metadata'],
        'club_id_to_idx': g['club_id_to_idx'],
        'idx_to_club_id': g['idx_to_club_id'],
        'player_id_to_idx': g['player_id_to_idx'],
        'idx_to_player_id': g['idx_to_player_id'],
        'coach_id_to_idx': g['coach_id_to_idx'],
        'idx_to_coach_id': g['idx_to_coach_id']
    }
    torch.save(checkpoint, save_path)
    print(f'[HGNN] Embeddings & Metadata successfully saved to: {save_path}')
    return checkpoint


if __name__ == '__main__':
    train_hgnn(epochs=60)
