# Automation and AI access

The public hostname `emfi.ics.red` is useful for operators and for automation,
but Control can move hardware and trigger high-voltage equipment. Automation
must authenticate, be scoped, and use higher-level campaign endpoints rather
than raw pulse/motion endpoints wherever possible.

## Authentication layers

Use two layers:

1. Cloudflare Access protects `https://emfi.ics.red` for every caller.
2. The EMFI APIs should grow an application-level automation token before any
   unattended agent is allowed to start campaigns.

Cloudflare Access service tokens are the right outer credential for agents.
Create a token per automation client and send it on every request:

```bash
curl https://emfi.ics.red/api/control/readyz \
  -H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" \
  -H "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET"
```

The application-level token should be an `Authorization: Bearer ...` token
checked by Control and Develop. Keep separate tokens for:

- read-only observers
- build/firmware agents
- campaign-launch agents
- operators with manual hardware privileges

Do not let an AI agent use a human browser session cookie as its credential.

## Automation contract

Agents should call a narrow, auditable flow:

1. `GET /api/control/readyz`
2. `GET /api/develop/projects`
3. `POST /api/develop/projects/{id}/build`
4. `POST /api/control/target/flash`
5. `POST /api/control/campaigns/preflight` (planned)
6. `POST /api/control/arm` only when a policy allows unattended arming
7. `POST /api/control/campaigns`
8. `GET /api/control/campaigns/{id}`
9. `POST /api/control/campaigns/{id}/stop` on budget or safety condition

Avoid direct calls to raw hardware endpoints such as `/shouter/pulse`,
`/motion/move_abs`, and Scaffold power routes from autonomous agents. Those
should remain manual/operator or policy-gated endpoints.

## Required API improvements before unattended attacks

- Add bearer-token middleware with scopes.
- Add `POST /campaigns/preflight` that validates hardware state, firmware
  provenance, safety limits, grid bounds, estimated pulse count, and stop
  conditions without starting a campaign.
- Add campaign budgets: max attempts, max runtime, max voltage, max pulse rate,
  allowed trigger modes, allowed rails.
- Add required campaign metadata: operator/agent id, objective, target board,
  target project/build, and notes.
- Add audit events for arm, flash, motion, power, pulse, campaign start/stop.
- Add a read-only endpoint for live state so agents do not scrape WebSocket
  traffic when polling is enough.

## Future dual-target setup

The upcoming setup adds:

- DUT slot MSPM0L2228 targeted by EMFI through ChipSHOUTER.
- Platform slot MSPM0L2228 targeted by voltage glitching through a
  ChipWhisperer Husky crowbar path.
- eCTF firmware projects with coordinated target/platform behavior.

Model this explicitly instead of overloading the existing single-target fields:

```text
rig/
  devices:
    emfi: ChipSHOUTER + Scaffold pgen/A0
    voltage_glitch: ChipWhisperer Husky crowbar
    dut_programmer: XDS110
    platform_programmer: XDS110 or shared debug probe
  targets:
    dut:
      power_rail: scaffold.dut
      uart_status: D3
      swd: D7/D9
    platform:
      power_rail: scaffold.platform
      uart_status: TBD
      glitcher: husky
```

Campaigns should eventually support multiple synchronized actions per attempt:

```json
{
  "timeline": [
    {"at_us": 0, "device": "scaffold", "action": "wait_for_trigger", "source": "dut.D0"},
    {"at_us": 1.2, "device": "chipshouter", "action": "emfi_pulse"},
    {"at_us": 1.6, "device": "husky", "action": "crowbar_pulse"}
  ]
}
```

That should be a protocol change, not a one-off host-script convention, because
the UI, preflight checks, audit log, and analysis pages all need to understand
which target was attacked by which mechanism.
