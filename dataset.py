import torch
import numpy as np
from torch.utils.data import DataLoader, IterableDataset
import control  # pip install python-control, pip install slycot (optional)
from lti import drss_matrices, dlsim


class LinearDynamicalDataset(IterableDataset):
    def __init__(self, nx=5, nu=1, ny=1, seq_len=500, strictly_proper=True, dtype="float32", normalize=True):
        super(LinearDynamicalDataset).__init__()
        self.nx = nx
        self.nu = nu
        self.ny = ny
        self.seq_len = seq_len
        self.strictly_proper = strictly_proper
        self.dtype = dtype
        self.normalize = normalize

    def __iter__(self):
        while True:  # infinite dataset
            # for _ in range(1000):
            sys = control.drss(states=self.nx,
                               inputs=self.nu,
                               outputs=self.ny,
                               strictly_proper=self.strictly_proper)
            u = np.random.randn(self.nu, self.seq_len).astype(self.dtype)  # C, T as python-control wants
            y = control.forced_response(sys, T=None, U=u, X0=0.0)
            u = u.transpose()  # T, C
            y = y.y.transpose().astype(self.dtype)  # T, C
            if self.normalize:
                y = (y - y.mean(axis=0)) / (y.std(axis=0) + 1e-6)

            yield torch.tensor(y), torch.tensor(u)


class WHDataset(IterableDataset):
    def __init__(self, nx=5, nu=1, ny=1, seq_len=500, strictly_proper=True, dtype="float32", normalize=True):
        super(WHDataset).__init__()
        self.nx = nx
        self.nu = nu
        self.ny = ny
        self.seq_len = seq_len
        self.strictly_proper = strictly_proper
        self.dtype = dtype
        self.normalize = normalize

    def __iter__(self):

        # A simple ff neural network
        def nn_fun(x):
            out = x @ w1.transpose() + b1
            out = np.tanh(out)
            out = out @ w2.transpose() + b2
            return out

        while True:  # infinite dataset
            # for _ in range(1000):

            n_in = 1
            n_out = 1
            n_hidden = 32

            w1 = np.random.randn(n_hidden, n_in) / np.sqrt(n_in) * 5 / 3
            b1 = np.random.randn(1, n_hidden) * 1.0
            w2 = np.random.randn(n_out, n_hidden) / np.sqrt(n_hidden)
            b2 = np.random.randn(1, n_out) * 1.0

            G1 = control.drss(states=self.nx,
                              inputs=self.nu,
                              outputs=self.ny,
                              strictly_proper=self.strictly_proper)

            G2 = control.drss(states=self.nx,
                              inputs=self.nu,
                              outputs=self.ny,
                              strictly_proper=False)

            u = np.random.randn(self.seq_len, self.nu).astype(self.dtype)  # C, T as python-control wants

            # G1
            y = control.forced_response(G1, T=None, U=u.transpose(), X0=0.0)
            y = y.y.astype(self.dtype).transpose()  # T, C
            y = (y - y.mean(axis=0)) / (y.std(axis=0) + 1e-6)

            # F
            y = nn_fun(y)

            # G2
            y = control.forced_response(G2, T=None, U=y.transpose(), X0=0.0)
            y = y.y.astype(self.dtype).transpose()

            if self.normalize:
                y = (y - y.mean(axis=0)) / (y.std(axis=0) + 1e-6)

            yield torch.tensor(y), torch.tensor(u)


class WHSmoothDataset(IterableDataset):
    def __init__(self, nx=5, nu=1, ny=1, seq_len=500, strictly_proper=True, dtype="float32", normalize=True):
        super(WHSmoothDataset).__init__()
        self.nx = nx
        self.seq_len = seq_len
        self.strictly_proper = strictly_proper
        self.dtype = dtype
        self.normalize = normalize
        self.strictly_proper = strictly_proper

    def __iter__(self):

        # A simple ff neural network
        def nn_fun(x):
            out = x @ w1.transpose() + b1
            out = np.tanh(out)
            out = out @ w2.transpose() + b2
            return out

        while True:  # infinite dataset
            # for _ in range(1000):

            n_in = 1
            n_out = 1
            n_hidden = 32

            w1 = np.random.randn(n_hidden, n_in) / np.sqrt(n_in) * 5 / 3
            b1 = np.random.randn(1, n_hidden) * 1.0
            w2 = np.random.randn(n_out, n_hidden) / np.sqrt(n_hidden)
            b2 = np.random.randn(1, n_out) * 1.0

            G1 = drss_matrices(states=self.nx,
                               inputs=1,
                               outputs=1,
                               strictly_proper=self.strictly_proper)

            G2 = drss_matrices(states=self.nx,
                               inputs=1,
                               outputs=1,
                               strictly_proper=False)

            u = np.random.randn(self.seq_len, 1)  # C, T as python-control wants

            # G1
            y = dlsim(*G1, u)
            y = (y - y.mean(axis=0)) / (y.std(axis=0) + 1e-6)

            # F
            y = nn_fun(y)

            # G2
            y = dlsim(*G2, y)

            if self.normalize:
                y = (y - y.mean(axis=0)) / (y.std(axis=0) + 1e-6)

            u = u.astype(self.dtype)
            y = y.astype(self.dtype)
            yield torch.tensor(y), torch.tensor(u)


if __name__ == "__main__":
    train_ds = WHSmoothDataset(nx=5, seq_len=1000)
    # train_ds = LinearDynamicalDataset(nx=5, nu=2, ny=3, seq_len=1000)
    train_dl = DataLoader(train_ds, batch_size=32)
    batch_y, batch_u = next(iter(train_dl))
    print(batch_u.shape, batch_u.shape)
