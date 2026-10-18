import { Buffer } from "buffer";

// circomlibjs / snarkjs / tlock expect Node's Buffer global in the browser.
(globalThis as unknown as { Buffer: typeof Buffer }).Buffer ??= Buffer;
