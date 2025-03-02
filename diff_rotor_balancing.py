# -*- coding: utf-8 -*-

pip install torch

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import dual_annealing

# Define the neural network model for the diffusion process
class DiffusionModel(nn.Module):
    def __init__(self, input_dim):
        super(DiffusionModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, input_dim)

    def forward(self, x, t):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x

# Function to calculate mass balance
def mass_balance_calculation(vectors):
    combined_vector = np.sum(list(vectors.values()), axis=0)
    return np.linalg.norm(combined_vector)

# Function to rotate vectors by specified angles
def rotate_vectors(vectors, angles):
    rotated_vectors = {}
    for i, (key, vector) in enumerate(vectors.items()):
        if key == 'shaft':
            rotated_vectors[key] = vector  # Shaft vector is not rotated
        else:
            angle = angles[i-1]  # Adjust index for disc vectors
            rotation_matrix = np.array([
                [np.cos(angle), -np.sin(angle), 0],
                [np.sin(angle), np.cos(angle), 0],
                [0, 0, 1]
            ])
            rotated_vectors[key] = np.dot(rotation_matrix, vector)
    return rotated_vectors

# Function to calculate vectors from shaft and disc data
def calculate_vectors(shaft_magnitude, shaft_angle, disc_data):
    vectors = {}
    vectors['shaft'] = np.array([
        shaft_magnitude * np.cos(shaft_angle),
        shaft_magnitude * np.sin(shaft_angle),
        0
    ])
    for index, row in disc_data.iterrows():
        disc_id = row['disc_id']
        disc_vector = np.array([
            row['disc_magnitude'] * np.cos(row['disc_angle']),
            row['disc_magnitude'] * np.sin(row['disc_angle']),
            0
        ])
        vectors[disc_id] = disc_vector
    return vectors

# Sample data input for dynamic balancing
shaft_magnitude = 0.05
shaft_angle = np.radians(45)  # Convert to radians

disc_data = pd.DataFrame({
    'disc_id': [1, 2, 3, 4],
    'disc_magnitude': [0.02, 0.03, 0.01, 0.04],
    'disc_angle': np.radians([0, 90, 180, 270])  # Convert to radians
})

# Calculate initial vectors
vectors = calculate_vectors(shaft_magnitude, shaft_angle, disc_data)

# Initialize the model, optimizer, and loss function
input_dim = len(disc_data)
model = DiffusionModel(input_dim)
optimizer = optim.Adam(model.parameters(), lr=0.001)
criterion = nn.MSELoss()

# Training parameters
num_epochs = 1000
timesteps = 100
noise_level = 0.1

# Training loop
for epoch in range(num_epochs):
    optimizer.zero_grad()

    # Generate noisy angles
    initial_angles = torch.tensor(np.random.uniform(0, 2 * np.pi, input_dim), dtype=torch.float32)
    noisy_angles = initial_angles + torch.randn_like(initial_angles) * noise_level

    # Forward pass
    t = torch.tensor([timesteps], dtype=torch.float32)
    predicted_angles = model(noisy_angles, t)

    # Calculate loss
    rotated_vectors = rotate_vectors(vectors, predicted_angles.detach().numpy())
    loss = criterion(predicted_angles, initial_angles)
    loss += torch.tensor(mass_balance_calculation(rotated_vectors), dtype=torch.float32)

    # Backward pass and optimization
    loss.backward()
    optimizer.step()

    if epoch % 100 == 0:
        print(f'Epoch {epoch}, Loss: {loss.item()}')

# Inference to find optimal angles
with torch.no_grad():
    initial_angles = torch.tensor(np.random.uniform(0, 2 * np.pi, input_dim), dtype=torch.float32)
    for t in reversed(range(timesteps)):
        t = torch.tensor([t], dtype=torch.float32)
        predicted_angles = model(initial_angles, t)
        initial_angles = predicted_angles

optimal_angles = initial_angles.numpy()
optimal_vectors = rotate_vectors(vectors, optimal_angles)

# Plotting results
def plot_3d_vectors(vectors, title='3D Vectors'):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    for key, vector in vectors.items():
        label = 'Shaft' if key == 'shaft' else f'Disc {key}'
        ax.quiver(0, 0, 0, vector[0], vector[1], vector[2], label=label)
    ax.set_title(title)
    ax.legend()
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z (unused)')
    plt.show()

def plot_polar(vectors, title='Polar Plot'):
    angles = [np.arctan2(vector[1], vector[0]) for vector in vectors.values()]
    magnitudes = [np.linalg.norm(vector) for vector in vectors.values()]
    plt.polar(angles, magnitudes, 'o')
    for i, (angle, magnitude) in enumerate(zip(angles, magnitudes)):
        label = 'Shaft' if i == 0 else f'Disc {i}'
        plt.annotate(label, (angle, magnitude))
    plt.title(title)
    plt.show()

plot_3d_vectors(optimal_vectors, title='Optimal 3D Vectors')
plot_polar(optimal_vectors, title='Optimal Polar Plot')

final_balance = mass_balance_calculation(optimal_vectors)
print("Optimal Angles (radians):", optimal_angles)
print("Final Mass Balance:", final_balance)
