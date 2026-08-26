import pandas as pd

from schema_detection.type_detector import detect_column_type


def test_numeric_strings_are_not_detected_as_dates():
    values = pd.Series(["5.0", "1.0", "3.0"] * 10)

    assert detect_column_type(values, "Quantity", len(values)) == "numeric"


def test_named_price_strings_are_detected_as_currency():
    values = pd.Series(["255.96", "514.01", "173.91"] * 10)

    assert detect_column_type(values, "Unit_Price", len(values)) == "currency"


def test_date_strings_remain_datetime():
    values = pd.Series(["12/05/2023", "11/08/2024", "13/03/2025"] * 10)

    assert detect_column_type(values, "Delivery_Date", len(values)) == "datetime"


def test_boolean_strings_are_detected_as_boolean():
    values = pd.Series(["yes", "no", "true", "false"] * 5)

    assert detect_column_type(values, "Is_Returning_Customer", len(values)) == "boolean"
