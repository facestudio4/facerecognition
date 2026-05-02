import os
import sys
import base64
import tempfile
import sqlite3

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.phase3_services_pack import Phase3ServiceHub


def load_image_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main():
    # Use a temp workspace to avoid touching user DB
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "smoke.db")
        # create minimal DB file
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY)")
        conn.commit()
        conn.close()

        hub = Phase3ServiceHub(base_dir=tmpdir, db_path=db_path)

        # pick an existing small image from project faces if available
        faces_root = os.path.join(hub.base_dir, "database", "faces")
        # fallback to project database faces if present under repository root
        project_faces = os.path.join(_project_root, "database", "faces")
        if os.path.isdir(project_faces):
            project_root = project_faces
        elif os.path.isdir(faces_root):
            project_root = faces_root
        else:
            print("No faces folder found to run smoke image test; exiting with success code 0")
            return 0

        # find any jpg/png under a person folder
        found = None
        for person in os.listdir(project_root):
            pdir = os.path.join(project_root, person)
            if not os.path.isdir(pdir):
                continue
            for fname in os.listdir(pdir):
                if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                    found = os.path.join(pdir, fname)
                    break
            if found:
                break

        if not found:
            print("No image found under faces/ to run smoke test; exiting")
            return 0

        print(f"Using sample image: {found}")
        img_b64 = load_image_b64(found)

        person = "SmokeTest_Person"
        print("Enrolling face via enroll_face_for_user()...")
        r = hub.enroll_face_for_user(person_name=person, image_b64=img_b64)
        print("enroll result:", r)

        print("Saving recognition location event (full coords)...")
        s1 = hub.save_recognition_location_event(
            recognized_name=person,
            location_name="Smokeville",
            latitude=12.34567,
            longitude=76.54321,
            confidence=0.91,
            requested_by="smoke",
        )
        print("save result:", s1)

        print("Saving recognition location event with missing label (should keep last known)...")
        s2 = hub.save_recognition_location_event(
            recognized_name=person,
            location_name="Location fetch failed",
            latitude=None,
            longitude=None,
            confidence=0.88,
            requested_by="smoke",
        )
        print("save2 result:", s2)

        print("Listing latest recognition locations...")
        rows = hub.list_latest_recognition_locations(limit=50)
        for r in rows:
            if str(r.get("recognized_name", "")).lower().startswith(person.lower()):
                print("Found latest for person:", r)
                break
        else:
            print("Person not found in latest list")

    return 0


if __name__ == "__main__":
    sys.exit(main())
