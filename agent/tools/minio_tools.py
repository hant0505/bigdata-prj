from crewai.tools import tool
import os


def _sync_silver_from_minio_impl(local_dir: str = None) -> str:
    """
    Implementation: Download all .parquet files under the `silver/` prefix from the MinIO bucket
    into the repository `data/` directory (or `local_dir` if provided).

    Returns a short summary string of downloaded files.
    """
    # Determine repo root (parent of agent/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(current_dir))

    if local_dir:
        target_dir = os.path.abspath(local_dir)
    else:
        target_dir = os.path.join(repo_root, "data")

    os.makedirs(target_dir, exist_ok=True)

    # Load MinIO configuration from etl.config to keep single source of truth
    try:
        import sys
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from etl.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, BUCKET_NAME
    except Exception as e:
        return f"Failed to load MinIO config from etl.config: {e}"

    # Import Minio lazily so module can be imported even if package not installed
    try:
        from minio import Minio
    except Exception:
        return "minio package not installed; run: pip install minio"

    # Create Minio client
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
    except Exception as e:
        return f"Failed to create MinIO client: {e}"

    downloaded = []
    try:
        for obj in client.list_objects(BUCKET_NAME, prefix="silver/", recursive=True):
            if obj.object_name.lower().endswith(".parquet"):
                dest_name = os.path.basename(obj.object_name)
                dest_path = os.path.join(target_dir, dest_name)
                # Skip if already exists and size matches (best-effort)
                if os.path.exists(dest_path) and os.path.getsize(dest_path) == obj.size:
                    continue
                client.fget_object(BUCKET_NAME, obj.object_name, dest_path)
                downloaded.append(dest_path)
    except Exception as e:
        return f"Error while listing/downloading objects: {e}"

    if not downloaded:
        return f"No parquet files downloaded. Target dir: {target_dir}"

    return f"Downloaded {len(downloaded)} files to {target_dir}: {', '.join([os.path.basename(p) for p in downloaded])}"


# CrewAI tool wrapper (for agent usage)
sync_silver_from_minio_tool = tool(_sync_silver_from_minio_impl)


# Exposed callable function for interactive use (import & call)
def sync_silver_from_minio(local_dir: str = None) -> str:
    return _sync_silver_from_minio_impl(local_dir)
