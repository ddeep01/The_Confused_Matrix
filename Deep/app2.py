import streamlit as st
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

# ----------------------------------
# Load Model + Encoders + Mappings
# ----------------------------------
model = joblib.load("engagement_xgb_model.pkl")
category_te_map = joblib.load("category_te_mapping.pkl")
numeric_features = joblib.load("numeric_features.pkl")
categorical_features = joblib.load("categorical_features.pkl")

cat_maps = joblib.load("categorical_mappings.pkl")
category_id_map = cat_maps["category_id"]
captions_flag_map = cat_maps["captions_flag"]

# ----------------------------------
# UI 
# ----------------------------------
st.title("🎯 YouTube Engagement Rate Predictor")
st.write("Enter video & channel details to predict engagement rate and find the optimal duration.")

# ----------------------------------
# Category Mapping (Readable Names)
# ----------------------------------
category_map = {
    1: "Film & Animation",
    2: "Autos & Vehicles",
    10: "Music",
    15: "Pets & Animals",
    17: "Sports",
    20: "Gaming",
    22: "People & Blogs",
    23: "Comedy",
    24: "Entertainment",
    25: "News & Politics",
    26: "How-to & Style",
    27: "Education",
    28: "Science & Technology",
    29: "Nonprofits & Activism"
}
category_name_to_id = {v: k for k, v in category_map.items()}

# ----------------------------------
# User Inputs
# ----------------------------------
category_name = st.selectbox("Category", list(category_name_to_id.keys()))
category_id = category_name_to_id[category_name]

captions_flag = st.selectbox("Captions Flag", ["True", "False"])
total_videos = st.number_input("Total Videos on Channel", min_value=1, value=100)
channel_age_days = st.number_input("Channel Age (days)", min_value=1, value=1000)
duration_minutes = st.slider("Video Duration (minutes)", 0.1, 120.0, 5.0)
publish_hour = st.slider("Publish Hour", 0, 23, 12)
publish_dayofweek = st.slider("Day of Week (0=Mon ... 6=Sun)", 0, 6, 3)
subscriber_count = st.number_input("Subscriber Count", min_value=0, value=10000)
is_hd = st.selectbox("Is HD?", [0, 1])
title = st.text_input("Video Title", "My Awesome Video!")

# ----------------------------------
# Feature Engineering (same as training)
# ----------------------------------
title_length = len(title)
title_words = len(title.split())
title_exclamation = title.count("!")
title_question = title.count("?")

subscriber_count_log = np.log1p(subscriber_count)

publish_hour_sin = np.sin(2 * np.pi * publish_hour / 24)
publish_hour_cos = np.cos(2 * np.pi * publish_hour / 24)
publish_dow_sin = np.sin(2 * np.pi * publish_dayofweek / 7)
publish_dow_cos = np.cos(2 * np.pi * publish_dayofweek / 7)

category_te = category_te_map.get(category_id, category_te_map.mean())

# ----------------------------------
# Build Base Input
# ----------------------------------
base_input = {
    "category_id": category_id,
    "captions_flag": captions_flag,
    "total_videos": total_videos,
    "channel_age_days": channel_age_days,
    "title_length": title_length,
    "title_words": title_words,
    "title_exclamation": title_exclamation,
    "title_question": title_question,
    "duration_minutes": duration_minutes,
    "publish_hour_sin": publish_hour_sin,
    "publish_hour_cos": publish_hour_cos,
    "publish_dow_sin": publish_dow_sin,
    "publish_dow_cos": publish_dow_cos,
    "subscriber_count_log": subscriber_count_log,
    "is_hd": is_hd,
    "category_te": category_te
}

# Convert to DataFrame ( BEFORE mapping )
input_df = pd.DataFrame([base_input])

# -------------------------------------------
# Apply SAME categorical encoding as training
# -------------------------------------------
input_df["category_id"] = str(category_id)
input_df["category_id"] = input_df["category_id"].map(category_id_map).astype(int)
input_df["captions_flag"] = input_df["captions_flag"].map(captions_flag_map).astype(int)

# -------------------------------------------
# Main Prediction
# -------------------------------------------
if st.button("Predict Engagement Rate"):
    pred = model.predict(input_df)[0]
    engagement_rate = np.exp(pred) - 1

    st.success(f"📈 **Predicted Engagement Rate:** {engagement_rate:.4f}")

    # ----------------------------------------------------
    # 🔥 Optimal Duration Chart
    # ----------------------------------------------------
    st.subheader("📊 Optimal Video Duration (Based on Model)")

    # Generate durations 1–120 minutes
    durations = np.arange(1, 121)

    duration_predictions = []

    for d in durations:
        temp = base_input.copy()
        temp["duration_minutes"] = d

        df_temp = pd.DataFrame([temp])

        # Apply categorical encoding
        df_temp["category_id"] = str(category_id)
        df_temp["category_id"] = df_temp["category_id"].map(category_id_map).astype(int)
        df_temp["captions_flag"] = df_temp["captions_flag"].map(captions_flag_map).astype(int)

        pred_d = model.predict(df_temp)[0]
        final_pred = np.exp(pred_d) - 1
        duration_predictions.append(final_pred)

    duration_predictions = np.array(duration_predictions)

    # Find optimal duration (max engagement)
    optimal_idx = np.argmax(duration_predictions)
    optimal_duration = durations[optimal_idx]
    optimal_engagement = duration_predictions[optimal_idx]

    # % improvement over user's duration
    improvement = ((optimal_engagement - engagement_rate) / engagement_rate) * 100

    # ----------------------
    # Plotting
    # ----------------------
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(durations, duration_predictions)
    ax.axvline(optimal_duration, linestyle='--')
    ax.set_xlabel("Duration (minutes)")
    ax.set_ylabel("Predicted Engagement Rate")
    ax.set_title("Duration vs Engagement Rate")

    st.pyplot(fig)

    # ----------------------
    # Show insights
    # ----------------------
    st.success(f"🔥 **Optimal Duration:** {optimal_duration} minutes")
    st.write(f"⭐ Engagement at optimal duration: **{optimal_engagement:.4f}**")
    st.write(f"📈 Improvement over your duration: **{improvement:.2f}%**")
