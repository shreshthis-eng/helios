"""
Adaboost-GA-BP Master Ensemble Model
Implementation of the full Adaboost-GA-BP algorithm (Paper Section 5.3).
Combines multiple GA-BP weak neural network predictors into one powerful strong predictor.
"""

import numpy as np
from .ga_bp import BPNeuralNetwork, GeneticAlgorithmOptimizer


class AdaboostGABPModel:
    """
    Adaboost-GA-BP Model for Short-Term Photovoltaic Power Forecasting.
    Combines Genetic Algorithm weight optimization with Adaboost boosting over T weak BP networks.
    """

    def __init__(self, n_estimators: int = 5, epochs_per_estimator: int = 20, learning_rate: float = 0.05):
        self.n_estimators = n_estimators
        self.epochs_per_estimator = epochs_per_estimator
        self.lr = learning_rate

        self.estimators = []
        self.estimator_weights = []

    def fit(self, X: np.ndarray, y: np.ndarray, run_ga: bool = True):
        """
        Trains the Adaboost-GA-BP model on input features X and target power y.
        """
        N, num_features = X.shape
        y = y.flatten()

        # Step 3: Initialize sample distribution weights D1(i) = 1/N
        D = np.ones(N) / N

        self.estimators = []
        self.estimator_weights = []

        for t in range(self.n_estimators):
            # Step 1: Create weak predictor (BP Neural Network)
            net = BPNeuralNetwork(input_dim=num_features, hidden_dim=19, output_dim=1, learning_rate=self.lr)

            # Step 2: GA Optimization for initial weights & biases
            if run_ga:
                ga = GeneticAlgorithmOptimizer(pop_size=20, generations=15, pc=0.8, pm=0.1)
                best_weights = ga.optimize(net, X, y)
                net.set_parameters_from_vector(best_weights)

            # Step 4: Train weak predictor with sample distribution D
            for epoch in range(self.epochs_per_estimator):
                net.train_epoch(X, y, sample_weights=D)

            preds = net.predict(X).flatten()
            abs_errors = np.abs(preds - y)

            # Normalized relative error e_i for regression boosting
            max_err = np.max(abs_errors)
            if max_err == 0:
                max_err = 1e-8
            rel_errors = abs_errors / max_err

            # Weighted error sum epsilon_t
            epsilon_t = np.sum(D * rel_errors)
            epsilon_t = np.clip(epsilon_t, 1e-6, 0.499999)

            # Step 5: Calculate coefficient of weak predictor alpha_t
            beta_t = epsilon_t / (1.0 - epsilon_t)
            alpha_t = 0.5 * np.log(1.0 / (beta_t + 1e-8))

            # Step 6: Adjust weight distribution D
            D = D * (beta_t ** (1.0 - rel_errors))
            Z_t = np.sum(D)
            if Z_t > 0:
                D = D / Z_t

            self.estimators.append(net)
            self.estimator_weights.append(alpha_t)

        # Normalize estimator weights
        total_w = np.sum(self.estimator_weights)
        if total_w > 0:
            self.estimator_weights = [w / total_w for w in self.estimator_weights]

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Step 7: Combine weak predictors into ultimate strong predictor:
        h(x) = sum( w_t * h_t(x) )
        """
        final_preds = np.zeros(X.shape[0])
        for net, weight in zip(self.estimators, self.estimator_weights):
            preds = net.predict(X).flatten()
            final_preds += weight * preds
        return final_preds
