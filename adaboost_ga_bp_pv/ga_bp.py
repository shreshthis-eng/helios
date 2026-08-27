"""
BP Neural Network & Genetic Algorithm (GA) Initializer
Implementation of the GA-BP hybrid optimization model (Paper Section 5.1 & 5.2).
Uses Genetic Algorithm to evolve optimal initial weights and biases for the BP Neural Network.
"""

import numpy as np


class BPNeuralNetwork:
    """
    3-Layer Backpropagation Neural Network (Input layer -> Hidden layer -> Output layer).
    Configured according to paper specs:
      - Inputs: 4 (GHI, DHI, Temperature, Wind Speed)
      - Hidden nodes: 19
      - Outputs: 1 (PV Power MW)
    """

    def __init__(self, input_dim: int = 4, hidden_dim: int = 19, output_dim: int = 1, learning_rate: float = 0.05):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.lr = learning_rate

        # Initialize weights and biases randomly (can be overwritten by GA)
        self.w1 = np.random.randn(input_dim, hidden_dim) * 0.1
        self.b1 = np.zeros((1, hidden_dim))
        self.w2 = np.random.randn(hidden_dim, output_dim) * 0.1
        self.b2 = np.zeros((1, output_dim))

    @property
    def num_parameters(self) -> int:
        """Total number of weights and biases (gene length for GA)."""
        return (self.input_dim * self.hidden_dim) + self.hidden_dim + (self.hidden_dim * self.output_dim) + self.output_dim

    def set_parameters_from_vector(self, param_vector: np.ndarray):
        """Unpack 1D chromosome vector into network weight matrices and bias vectors."""
        idx = 0

        # w1: (input_dim, hidden_dim)
        w1_size = self.input_dim * self.hidden_dim
        self.w1 = param_vector[idx : idx + w1_size].reshape(self.input_dim, self.hidden_dim)
        idx += w1_size

        # b1: (1, hidden_dim)
        self.b1 = param_vector[idx : idx + self.hidden_dim].reshape(1, self.hidden_dim)
        idx += self.hidden_dim

        # w2: (hidden_dim, output_dim)
        w2_size = self.hidden_dim * self.output_dim
        self.w2 = param_vector[idx : idx + w2_size].reshape(self.hidden_dim, self.output_dim)
        idx += w2_size

        # b2: (1, output_dim)
        self.b2 = param_vector[idx : idx + self.output_dim].reshape(1, self.output_dim)

    def get_parameters_vector(self) -> np.ndarray:
        """Pack all network weights and biases into a 1D vector."""
        return np.concatenate([
            self.w1.flatten(),
            self.b1.flatten(),
            self.w2.flatten(),
            self.b2.flatten()
        ])

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        """Sigmoid activation function."""
        return 1.0 / (1.0 + np.exp(-np.clip(x, -15.0, 15.0)))

    @staticmethod
    def _sigmoid_derivative(output: np.ndarray) -> np.ndarray:
        """Derivative of sigmoid given its output."""
        return output * (1.0 - output)

    def forward(self, X: np.ndarray) -> tuple:
        """Forward pass through network."""
        z1 = np.dot(X, self.w1) + self.b1
        a1 = self._sigmoid(z1)

        z2 = np.dot(a1, self.w2) + self.b2
        a2 = z2  # Linear activation for output regression layer
        return a1, a2

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Returns predictions for input matrix X."""
        _, predictions = self.forward(X)
        return predictions

    def train_epoch(self, X: np.ndarray, y: np.ndarray, sample_weights: np.ndarray = None) -> float:
        """
        Performs one epoch of Backpropagation gradient descent with optional sample weights.
        Returns Mean Squared Error (MSE).
        """
        N = X.shape[0]
        if sample_weights is None:
            sample_weights = np.ones((N, 1)) / N
        else:
            sample_weights = sample_weights.reshape(-1, 1)

        # Forward pass
        a1, a2 = self.forward(X)

        # Error
        error = a2 - y.reshape(-1, 1)
        weighted_error = error * sample_weights

        # Backward pass
        dw2 = np.dot(a1.T, weighted_error)
        db2 = np.sum(weighted_error, axis=0, keepdims=True)

        da1 = np.dot(weighted_error, self.w2.T)
        dz1 = da1 * self._sigmoid_derivative(a1)

        dw1 = np.dot(X.T, dz1)
        db1 = np.sum(dz1, axis=0, keepdims=True)

        # Update weights and biases
        self.w2 -= self.lr * dw2
        self.b2 -= self.lr * db2
        self.w1 -= self.lr * dw1
        self.b1 -= self.lr * db1

        mse = np.mean(error ** 2)
        return float(mse)


class GeneticAlgorithmOptimizer:
    """
    Genetic Algorithm (GA) for optimizing initial BP Neural Network weights & biases.
    Prevents BP network from falling into local minima traps.
    Parameters match Paper Section 5.2:
      - Crossover Probability Pc = 0.8
      - Mutation Probability Pm = 0.1
    """

    def __init__(
        self,
        pop_size: int = 30,
        generations: int = 25,
        pc: float = 0.8,
        pm: float = 0.1,
        param_bounds: tuple = (-1.0, 1.0)
    ):
        self.pop_size = pop_size
        self.generations = generations
        self.pc = pc
        self.pm = pm
        self.bounds = param_bounds

    def optimize(self, base_nn: BPNeuralNetwork, X_train: np.ndarray, y_train: np.ndarray) -> np.ndarray:
        """
        Runs genetic evolution to find optimal chromosome parameter vector.
        """
        num_genes = base_nn.num_parameters
        # Initialize population randomly within bounds
        population = np.random.uniform(self.bounds[0], self.bounds[1], (self.pop_size, num_genes))

        best_chromosome = population[0].copy()
        best_fitness = -1e9

        for gen in range(self.generations):
            fitness_scores = np.zeros(self.pop_size)

            # Evaluate fitness (inverse of MSE)
            for i in range(self.pop_size):
                base_nn.set_parameters_from_vector(population[i])
                preds = base_nn.predict(X_train)
                mse = np.mean((preds.flatten() - y_train.flatten()) ** 2)
                fitness = 1.0 / (mse + 1e-6)
                fitness_scores[i] = fitness

                if fitness > best_fitness:
                    best_fitness = fitness
                    best_chromosome = population[i].copy()

            # Selection (Roulette Wheel)
            probs = fitness_scores / np.sum(fitness_scores)
            selected_indices = np.random.choice(self.pop_size, size=self.pop_size, p=probs)
            population = population[selected_indices]

            # Crossover
            next_pop = []
            for i in range(0, self.pop_size, 2):
                parent1 = population[i].copy()
                parent2 = population[(i + 1) % self.pop_size].copy()

                if np.random.rand() < self.pc:
                    cross_point = np.random.randint(1, num_genes)
                    child1 = np.concatenate([parent1[:cross_point], parent2[cross_point:]])
                    child2 = np.concatenate([parent2[:cross_point], parent1[cross_point:]])
                else:
                    child1, child2 = parent1, parent2

                next_pop.extend([child1, child2])

            population = np.array(next_pop[: self.pop_size])

            # Mutation
            for i in range(self.pop_size):
                if np.random.rand() < self.pm:
                    mutate_idx = np.random.randint(0, num_genes)
                    population[i, mutate_idx] += np.random.normal(0, 0.2)
                    population[i, mutate_idx] = np.clip(population[i, mutate_idx], self.bounds[0], self.bounds[1])

        # Return best parameters vector found
        return best_chromosome
