# Prefer supported SiMa capabilities and artifacts

Apply this when selecting or replacing application components, models, or runtime
artifacts. Preserve the user's explicit model, repository, camera and transport
choices. Running an existing working package does not require redesigning it or
benchmarking unrelated alternatives.

## Discover before choosing

1. Read the selected SDK version, board type, runtime and application input/output
   contract. Inspect the installed SiMa skills, Neat applications, `sima-core`
   capability catalogue (`list_ros_capabilities` for an open ROS workspace), and
   the Studio model catalogue. Search by the required function, not just a familiar
   model name; inspect relevant descriptions and configuration files.
2. Query the SiMa Model Zoo for the observed target and SDK version. Studio exposes
   `GET /modelzoo/models?version=<observed-version>&boardtype=<observed-boardtype>`;
   use its advertised API or the installed `sima-cli modelzoo --help` and subcommand
   help to discover the supported listing/download syntax. Do not rely on the
   default release alias or an old model list. Inspect existing downloaded assets
   before downloading again.
3. Separate an empty matching result from failed discovery. Record catalogue
   authentication, connectivity or version errors as unresolved discovery, not
   evidence that SiMa has no suitable model. Retry a relevant supported discovery
   route; if still blocked, explain the limitation and continue independent work.

## Map every feature to a capability before writing a node

Do this before authoring any driver, camera, perception, SLAM/navigation, voice
or visualisation node, including on a clean board with a short prompt. Search
the whole SiMa offering, not only the workspace you happened to open:

- **`sima-core` capabilities.** Read `list_ros_capabilities`, then list the
  `capabilities/` tree itself, because the catalogue can miss nested packages
  (for example a capability whose package sits several directories down). Check
  at least the slam, navigation, voice_control and camera_publisher families
  and any detection capability before writing an equivalent.
- **Other SiMa organisation repositories.** List the SiMa GitHub organisations
  available through the stored credential (for example the SiMa robot sensor
  stack repository, which carries USB and depth camera drivers) and search them
  by function. A private repository the credential can read is in scope; one it
  cannot read is unresolved discovery, not absence.
- **SiMa Model Zoo** through Studio's model download path (see step 2 above),
  and models already downloaded into the workspace.
- **Studio's bundled surfaces:** Flora for live visualisation
  (`edgematic-foxglove-viz`), Streams for RTSP input, and the operator TUI flow
  (`edgematic-robot-tui`).

Write the mapping into the project's `docs/component-selection.md` before
generating code: one row per requested feature with the selected capability or
artifact (repository, path, revision), the alternatives checked, and for every
custom node the specific reason no SiMa option fits (contract mismatch, failed
smoke test, missing artifact, licence, explicit user requirement). A custom
node without that row is not ready to write. Revisit the mapping when the user
asks whether a SiMa capability was used; answer from the table.

### Voice defaults

When the request includes speech input or output and names no stack, choose the
SiMa on-board path and state it instead of asking:

- **Speech to text:** the `sima-core` `voice_control` transcription path against
  the board's on-board Whisper endpoint served through LLiMa
  (`/v1/audio/transcriptions`); a transcription-only flow does not need an LLM.
- **Text to speech:** SiMa's Piper TTS voice provider.
- **No cloud API keys** unless the user explicitly asks for a cloud service.
- **Fixed command sets:** when the user wants a small set of commands, constrain
  recognition to that grammar or keyword list and map each to an intent, rather
  than free-form dictation.
- **Devices:** open microphones and speakers by ALSA card name
  (`edgematic-ros2-board-setup`, stable device names), never a numeric card.
- **Safety:** a voice intent may select a behaviour that the command owner
  accepts while already armed; it can never arm, disarm-override or bypass a
  motion guard ([attended robot motion](../../edgematic-ros2-contract-builder/references/attended-motion.md)).

If a SiMa voice component fails its smoke test on the target, record the
evidence and fall back as for any other component.

## Reuse what fits

Prefer compatible SiMa precompiled artifacts, Neat runtime components, ROS
capabilities, parsers and examples before a new external dependency, custom model
export/compilation, or duplicate inference runtime. Inspect the artifact's actual
manifest and example contract: architecture/accelerator, supported SDK/runtime,
input names/shapes/layout/color order/normalization, output tensors/labels and
postprocessing, licenses and available provenance. A matching task label does
not prove compatibility, and a catalogue entry is not proof of a working model.

For a relevant, compatible SiMa candidate, run a scoped smoke test on the selected
or equivalent paired target before adopting an external/custom replacement.
Measure correct outputs and the application's relevant latency, throughput and
resource limits with representative input; label synthetic smoke tests and keep
accelerator inference timing separate from end-to-end timing. Reuse existing
current evidence when target, artifact hash and input contract match. A documented
contract mismatch can reject a candidate without a pointless deployment. Do not
interrupt an active workload or move hardware to test an optional alternative.

If custom work remains necessary, implement only the missing application logic
or adapter around the supported components. Valid reasons include a demonstrated
unsupported input/output contract, failed acceptance test, unavailable compatible
artifact, licensing restriction, explicit user requirement, or measured resource
constraint. State which SiMa option was checked and the specific evidence; do not
say “SiMa does not support this” from memory or from one failed search. Avoid
claiming all computation is accelerated when preprocessing, tracking, policy or
rendering still runs on the CPU.

## Keep project evidence, not hardware profiles

Record selections in the project's `docs/component-selection.md` (or its existing
evidence manifest): requirement; queried catalogue/version/target and result;
selected and rejected candidates; source URL and immutable revision/version;
artifact SHA-256; preprocessing/postprocessing and runtime contract; license
status; test method, measurements and log paths; unresolved gaps; and the reason
for any external/custom component. Separate observed facts from assumptions and
unknown original download sources. A local hash establishes identity, not origin.

Use this evidence for the README, demo FAQ and architecture: identify reused SiMa
parts and the specific integration or application logic authored for this project.
Keep model identifiers, measured performance, robot facts and customer repository
URLs in those project artifacts, never in shared skills. Optional model comparison
must not block unrelated working functionality; a required unverified component
must remain explicitly unverified.
