import pandas as pd


def predict_remaining_humidity(room_name, day_name, current_hour, model, data):
    all_hours = [
        "09:00",
        "10:00",
        "11:00",
        "12:00",
        "13:00",
        "14:00",
        "15:00",
        "16:00",
        "17:00",
    ]

    known_data = data[(data["room"] == room_name) & (data["day"] == day_name)]
    known_data = known_data[known_data["hour"] <= current_hour].sort_values("hour")

    if known_data.empty:
        raise ValueError("Aucune donnée connue pour cette salle et ce jour")

    predictions = {
        "room": {
            "name": room_name,
            "id": room_name,
            "days": {day_name: {"temperature": {}, "humidity": {}, "airPressure": {}}},
        }
    }

    last_known = known_data.copy()
    start_idx = all_hours.index(current_hour) + 1

    for hour in all_hours[start_idx:]:
        row = last_known.iloc[-1].copy()
        row["hour"] = hour
        row["day"] = day_name
        row["room"] = room_name

        temp_df = pd.DataFrame([row])

        if hasattr(model, "feature_names_in_"):
            temp_df = pd.get_dummies(temp_df)
            for col in model.feature_names_in_:
                if col not in temp_df.columns:
                    temp_df[col] = 0
            temp_df = temp_df[model.feature_names_in_]

        predicted_humidity = round(model.predict(temp_df)[0], 1)

        predictions["room"]["days"][day_name]["humidity"][hour] = predicted_humidity
        predictions["room"]["days"][day_name]["temperature"][hour] = float(
            row.get("temperature", 0)
        )
        predictions["room"]["days"][day_name]["airPressure"][hour] = float(
            row.get("airPressure", 0)
        )

        row["humidité"] = predicted_humidity
        last_known = pd.concat([last_known, pd.DataFrame([row])], ignore_index=True)

    return predictions
