# Environment Detection — Dual-Mode Safety

## Overview
Added environment detection to guard Streamlit imports across core modules. This prevents import errors if these modules are ever used in non-Streamlit contexts (e.g., desktop app, CLI tools).

## Implementation

### New File: `utils/env_helpers.py`
```python
import os

# Streamlit sets this environment variable when running
IS_STREAMLIT = "STREAMLIT_SERVER_RUNNING" in os.environ
```

### Updated Files

#### 1. `services/subscription.py`
```python
from utils.env_helpers import IS_STREAMLIT

if IS_STREAMLIT:
    import streamlit as st
else:
    st = None
```
- Guarded Streamlit import
- `st` is `None` when not in Streamlit environment
- All `st` calls are inside functions only called from app.py

#### 2. `utils/session_helpers.py`
```python
from utils.env_helpers import IS_STREAMLIT

if IS_STREAMLIT:
    import streamlit as st
else:
    st = None
```
- Guarded Streamlit import
- `st` is `None` when not in Streamlit environment
- All functions using `st` are only called from app.py

#### 3. `core/feature_gate.py`
```python
from utils.env_helpers import IS_STREAMLIT

if IS_STREAMLIT:
    import streamlit as st
else:
    st = None
```
- Guarded Streamlit import
- Safe for future imports from other contexts

#### 4. `services/usage_tracker.py`
```python
from utils.env_helpers import IS_STREAMLIT

if IS_STREAMLIT:
    import streamlit as st
else:
    st = None
```
- Guarded Streamlit import
- Session state functions only called from app.py

## Safety Properties

✅ **Desktop Mode (app_desktop.py)**
- Does NOT import any of these modules
- Uses only coltradata.engine
- Runs without any Streamlit dependencies

✅ **Streamlit Mode (app.py)**
- Sets `STREAMLIT_SERVER_RUNNING` environment variable
- All modules import Streamlit normally
- All feature gates work as expected

✅ **Future-Proof**
- If these modules are ever imported in non-Streamlit contexts, they won't fail
- The `st = None` pattern allows graceful degradation
- Clear indication of which code requires Streamlit

## Testing

All files verified:
- ✅ No syntax errors
- ✅ All imports resolve correctly
- ✅ Both Streamlit and desktop modes remain functional

## Usage Pattern

If you need to add similar guards to other modules:

```python
from utils.env_helpers import IS_STREAMLIT

if IS_STREAMLIT:
    import streamlit as st
else:
    st = None

# Rest of imports...

def some_function():
    # st is available here in Streamlit mode
    # st is None in desktop mode (won't be called from desktop anyway)
    if IS_STREAMLIT:
        st.write("Hello from Streamlit!")
```
