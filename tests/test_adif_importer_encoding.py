import adif.importer as importer


class FakeAdifIO:
    def __init__(self):
        self.file_calls = []
        self.string_calls = []

    def read_from_file(self, filepath, encoding=None):
        self.file_calls.append((filepath, encoding))
        return ([{"CALL": "R1BQE"}], {})

    def read_from_string(self, content):
        self.string_calls.append(content)
        return ([{"CALL": "R1BQE", "GRIDSQUARE": "ТРОИЦКОЕ"}], {})


def test_cp1251_file_uses_regular_reader(tmp_path, monkeypatch):
    fake = FakeAdifIO()
    monkeypatch.setattr(importer, "adif_io", fake)
    path = tmp_path / "cp1251.adi"
    path.write_bytes("<CALL:5>R1BQE<EOR>".encode("cp1251"))

    result = importer.import_adif_file(path)

    assert result.success
    assert result.data["qsos"][0]["call"] == "R1BQE"
    assert fake.string_calls
    assert "R1BQE" in fake.string_calls[0]


def test_utf8_file_uses_regular_reader(tmp_path, monkeypatch):
    fake = FakeAdifIO()
    monkeypatch.setattr(importer, "adif_io", fake)
    path = tmp_path / "utf8.adi"
    path.write_text("<CALL:5>R1BQE<NAME:4>ИВАН<EOR>", encoding="utf-8")

    result = importer.import_adif_file(path)

    assert result.success
    assert "R1BQE" in fake.string_calls[0]


def test_mixed_cp1251_and_utf8_values_are_normalized(tmp_path, monkeypatch):
    fake = FakeAdifIO()
    monkeypatch.setattr(importer, "adif_io", fake)
    raw = (
        "<CALL:5>R1BQE".encode("ascii")
        + "<NAME:7>АЛЕКСЕЙ".encode("cp1251")
        + "<GRIDSQUARE:16>".encode("ascii")
        + "ТРОИЦКОЕ".encode("utf-8")
        + "<EOR>".encode("ascii")
    )
    path = tmp_path / "mixed.adi"
    path.write_bytes(raw)

    result = importer.import_adif_file(path)

    assert result.success
    normalized = fake.string_calls[0]
    assert "<NAME:7>АЛЕКСЕЙ" in normalized
    assert "<GRIDSQUARE:8>ТРОИЦКОЕ" in normalized
    assert "<GRIDSQUARE:16>" not in normalized
