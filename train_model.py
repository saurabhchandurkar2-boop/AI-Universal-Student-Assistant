import os
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

# Load dataset
data = pd.read_csv("dataset/students.csv")

print("Dataset Loaded Successfully!")
print(data)

# Features
X = data[["study_hours", "attendance", "assignments"]]

# Target
y = data["marks"]

# Train model
model = RandomForestRegressor(random_state=42)
model.fit(X, y)

# Create models folder if it doesn't exist
os.makedirs("models", exist_ok=True)

# Save model
with open("models/student_model.pkl", "wb") as file:
    pickle.dump(model, file)

print("\nModel Trained Successfully!")
print("Model saved in models/student_model.pkl")