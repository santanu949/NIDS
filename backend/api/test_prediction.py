import json
import urllib.request

import pandas as pd


# --------------------------------------------------
# Load one real UNSW-NB15 sample
# --------------------------------------------------

with open(
    "backend/data/feature_schema.json",
    encoding="utf-8",
) as f:
    schema = json.load(f)

df = pd.read_csv(
    "backend/data/raw/UNSW_NB15_training-set.csv",
    encoding="utf-8-sig",
)

sample = df.iloc[0]

features = {
    feature: sample[feature]
    for feature in schema["final_feature_order"]
}


# Convert NumPy values to normal Python values
for key, value in features.items():
    if hasattr(value, "item"):
        features[key] = value.item()


payload = json.dumps(
    {"features": features}
).encode("utf-8")


def call_api(endpoint):
    request = urllib.request.Request(
        f"http://127.0.0.1:8000{endpoint}",
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


print("NIDS API END-TO-END TEST")
print("=" * 65)

print("Dataset sample index:", 0)
print("Expected binary label:", int(sample["label"]))
print("Expected attack category:", str(sample["attack_cat"]).strip())
print()

binary_result = call_api(
    "/predict/binary"
)

multiclass_result = call_api(
    "/predict/multiclass"
)

print("BINARY RESPONSE")
print(binary_result)

print()
print("MULTICLASS RESPONSE")
print(multiclass_result)

print()
print("API VERIFICATION")
print("=" * 65)

binary_valid = (
    binary_result["prediction"] in [0, 1]
    and binary_result["label"]
    in ["Normal", "Attack"]
    and 0.0
    <= binary_result["confidence"]
    <= 1.0
)

multiclass_valid = (
    0
    <= multiclass_result["prediction"]
    < 10
    and isinstance(
        multiclass_result["label"],
        str,
    )
    and 0.0
    <= multiclass_result["confidence"]
    <= 1.0
)

print("Binary response valid:", binary_valid)
print("Multiclass response valid:", multiclass_valid)

print(
    "END-TO-END VERIFICATION:",
    "PASS"
    if binary_valid and multiclass_valid
    else "FAIL",
)