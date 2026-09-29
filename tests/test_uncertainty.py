from transcription_eval.uncertainty import bootstrap_detection


def test_one_meeting_does_not_manufacture_confidence_from_variants():
    refs = {("a", "c"): "fail", ("b", "c"): "fail"}
    assert bootstrap_detection(refs, refs, {"a": "same", "b": "same"}) is None


def test_reproducible_cluster_interval():
    refs = {("a", "c"): "fail", ("b", "c"): "fail"}
    predictions = {("a", "c"): "fail", ("b", "c"): "pass"}
    first = bootstrap_detection(refs, predictions, {"a": "one", "b": "two"})
    assert first == bootstrap_detection(refs, predictions, {"a": "one", "b": "two"})
    assert first["lower"] == 0 and first["upper"] == 1
