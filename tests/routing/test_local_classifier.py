from faultpilot.routing.local_classifier import LocalIntentClassifier


def test_local_classifier_detects_alarm_lookup() -> None:
    classifier = LocalIntentClassifier()

    result = classifier.classify("What does AL-09 mean?")

    assert result.intent == "alarm_lookup"
    assert result.confidence >= 0.8


def test_local_classifier_detects_programming() -> None:
    classifier = LocalIntentClassifier()

    result = classifier.classify("How to use a ladder timer instruction in PLC?")

    assert result.intent == "programming"
    assert result.confidence >= 0.8


def test_local_classifier_defaults_to_troubleshooting() -> None:
    classifier = LocalIntentClassifier()

    result = classifier.classify("The spindle motor overheats during operation")

    assert result.intent == "troubleshooting"
    assert result.confidence >= 0.5
