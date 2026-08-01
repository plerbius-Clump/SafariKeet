# Agent setup from a phone

This flow assumes a user is connected to their own Mac over SSH and is asking a
local coding agent to prepare SafaraKeet. The agent must read `AGENTS.md` first.

## Safe agent prompt

```text
Set up SafaraKeet from this repository. Read AGENTS.md first.

1. Run ./scripts/doctor.sh --json and report only its scrubbed capability summary.
2. Do not paste raw host, network, account, filesystem, process, or Tailscale output.
3. Do not install system packages, download a model, or configure private sharing
   until I explicitly approve that action.
4. If the profile is live-mlx and prerequisites are ready, ask before running:
   ./scripts/setup-local.sh --profile live-mlx --prefetch-model --build
5. After setup, install the local user service with:
   ./scripts/service.sh install
6. Configure private sharing only when I ask by running ./scripts/share.sh.
7. Verify with ./scripts/doctor.sh --json and ./scripts/check.sh.
```

## Agent decision flow

1. `./scripts/doctor.sh --json` performs read-only, privacy-scrubbed capability
   detection. It reports only coarse platform, memory, disk, tool, and model-cache
   states.
2. `live-mlx` is the supported live profile for an Apple-silicon Mac. An
   unsupported profile is a stop condition, not permission to install random STT
   software.
3. The model prefetch is explicit because it may download model files. The setup
   command is safe to rerun.
4. `./scripts/service.sh install` creates only ignored local service state and
   keeps the backend bound to loopback. It allows the app to survive the SSH
   session ending.
5. `./scripts/share.sh` is a separate opt-in because it changes private network
   exposure. Open the resulting `<private-https-address>` only on an authorized
   device in the same tailnet.

## Verification

```sh
./scripts/doctor.sh --json
./scripts/check.sh
./scripts/service.sh check
./scripts/service.sh status
```

Then verify on mobile Safari: allow the microphone, speak until live English
appears, use Pause & save, copy or archive the block, and restore it from the
Archived history tab.
