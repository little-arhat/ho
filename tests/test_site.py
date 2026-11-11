import json

from ho.site import embed_json


def test_embed_json_cannot_open_tags():
    text = str(embed_json({"a": "</script><!--<script>"}))
    assert "<" not in text
    assert json.loads(text) == {"a": "</script><!--<script>"}
