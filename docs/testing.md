# Testing

Run `pytest -q` from `backend/`. The current suite covers sample topology validation, TCP sequence wraparound, a disabled transit link, UDP closed-port semantics, DNS A lookup and HTTP success.

The tests are intentionally executable and limited to implemented behavior. Expand integration and browser coverage before claiming full acceptance of the larger academic specification.
