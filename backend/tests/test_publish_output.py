"""Testes de publicação na pasta de saída do usuário."""

from pathlib import Path

from PIL import Image as PILImage

from backend.api.workspace import publish_to_user_output


def test_publish_to_user_output(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace_output"
    workspace.mkdir()
    user_dest = tmp_path / "saida_usuario"

    docx = workspace / "E116_relatorio.docx"
    docx.write_bytes(b"PK fake docx")

    photos = workspace / "fotos_relatorio"
    photos.mkdir()
    img = PILImage.new("RGB", (8, 8), color=(1, 2, 3))
    img.save(photos / "1-IMG_0098.JPG")

    result = publish_to_user_output(workspace, user_dest)

    assert Path(result["report_path"]).is_file()
    assert Path(result["photos_dir"]).is_dir()
    assert (Path(result["photos_dir"]) / "1-IMG_0098.JPG").is_file()
    assert result["output_dir"] == str(user_dest.resolve())
