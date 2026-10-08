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
