"""Service launcher of the netns testbed: plain HTTP like the node's arm D (experiments_tnsm/m3_distributed/launcher_d.py): service._HTTP_TLS is set from OUTSIDE with a PREBUILT
SSL context, so that httpx does not rebuild the default SSL context at every call (6 ms each; 10 parallel deliveries serialised by the GIL cost ~0.4 s at the testbed).
service.py is NOT modified. Env: DIB_TESTBED_PORT (default 8000), DIB_TESTBED_HOST."""
import os
import ssl

import uvicorn

import service  # PYTHONPATH includes the distributed directory (uvicorn --app-dir equivalent)

service._HTTP_TLS = {"verify": ssl.create_default_context()}
uvicorn.run(service.app, host=os.environ.get("DIB_TESTBED_HOST", "127.0.0.1"), port=int(os.environ.get("DIB_TESTBED_PORT", "8000")), log_level="warning")
