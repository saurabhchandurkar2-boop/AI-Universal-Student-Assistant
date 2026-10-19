import os
import pickle

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "student_model.pkl")
DATA_PATH = os.path.join(BASE_DIR, "dataset", "students.csv")


def _train_model():
    """Train the model from dataset/students.csv and save it."""
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor

    data = pd.read_csv(DATA_PATH)
    X = data[["study_hours", "attendance", "assignments"]]
    y = data["marks"]
    new_model = RandomForestRegressor(random_state=42)
    new_model.fit(X, y)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as file:
        pickle.dump(new_model, file)
    return new_model


def _load_model():
    # If the saved model is missing or was made with a different
    # scikit-learn version, train a fresh one from the dataset.
    try:
        with open(MODEL_PATH, "rb") as file:
            return pickle.load(file)
    except Exception:
        return _train_model()


model = _load_model()


def predict_marks(study_hours, attendance, assignments):
    import pandas as pd

    features = pd.DataFrame(
        [[study_hours, attendance, assignments]],
        columns=["study_hours", "attendance", "assignments"]
    )
    prediction = model.predict(features)
    # Marks are out of 100.
    return round(float(min(max(prediction[0], 0), 100)), 2)
