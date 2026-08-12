# Demo 9 — Vision

## What this shows

- `VisionSensorType` describes physical and simulated sensors with the same contract.
- Media is brokered by endpoints, not moved through ordinary OPC UA variables.
- An inference pipeline points to an AI Model Management deployment by `NodeId`.
- Results have standard shapes: inspection characteristics, detections, poses, segmentations and feedback.

## What it proves

It proves the missing layer between existing OPC UA machine vision specifications and real integrations. OPC 40100-1 orchestrates jobs but leaves result content application-specific, and OPC 40010-1 has no camera, perception or calibration model. This draft defines the shape that lets two Servers publish comparable results.

## Prerequisites

- This repository.
- The Vision draft and generated NodeSet under `metaverse-specs\vision`.
- The Data Channels draft for the optional in-band media path.
- The AI Model Management draft for the deployment that interprets the image.

## Where the code is

An implementation exists on the stack branch `marcschier/vision-guided-picking`:
`Opc.Ua.Vision`, `Opc.Ua.Vision.Client`, `Opc.Ua.Vision.Server`, `Opc.Ua.Vision.OpenUsd` and
`Tools\Opc.Ua.Mcp.Vision`, plus a `samples\Robotics\BinPickingCell` server and a paired
`samples\Robotics\BinPickingClient`.

**It is not runnable end to end yet, so this demo has no script.** The branch is under active
development: at the time of writing its committed head does not compile, and with the author's
local fixes applied the scripted client loop still fails — `RunInference` returns a `ResultId` the
pipeline never publishes. Present this one as paper and say the implementation is in flight. Do not
promise a terminal.

That implementation is worth talking about even though it does not run, because it is what moved
the draft from 0.1.0 to 0.2.0 — see `metaverse-specs\vision\CHANGELOG.md`.

## How to present it without running it

Open the draft and use its architecture diagram and type inventory:

```powershell
code metaverse-specs\vision\OPC-UA-Vision.md
code metaverse-specs\vision\Opc.Ua.Vision.NodeSet2.xml
code metaverse-specs\ai-model-management\OPC-UA-AI-Model-Management.md
code core-specs\data-channels\OPC-UA-Data-Channels.md
```

## Step by step

1. **Start at the sensor.** Show clause 4.2 and `VisionSensorType`. Say: "A client starts at `Server/Vision/Sensors`; it does not need to know whether the sensor is physical or simulated."
2. **Show media as a brokered resource.** Show clause 6. Say: "The model describes how to obtain a stream or clip. It does not put video frames in ordinary variables."
3. **Connect the AI deployment.** Show clause 8.1 and the AI Model Management draft. Say: "The pipeline points to the deployment that runs the model; that is how a result remains auditable."
4. **Show the standard result shape.** Show `InspectionResultType`, `DetectionResultType` and `VisionPose3DDataType`. Say: "This is the part existing OPC UA vision work leaves undefined."
5. **End with feedback.** Show the feedback and learning sections. Say: "Corrections are not comments in a log. They are data that can feed the next training dataset."

## Talking points

- The default path brokers media by reference; Data Channels are optional.
- `RealityKind` is the only sim-versus-real discriminator a client should need.
- A result names frames and calibration, so a pose can be acted on by a robot.
- AI Model Management answers which model produced the result.
- The draft deliberately avoids depending on OPC 40100, OPC 40010, DI or OpenUSD in the base profile.

## Troubleshooting

- If someone asks to run it, say the implementation is in progress on `marcschier/vision-guided-picking` and does not yet run the loop end to end.
- If a camera transport question comes up, keep GenICam and GigE Vision below this model; this draft is the semantic and control layer.
- If media transport dominates the conversation, separate the default brokered endpoint from the optional Data Channel facet.
- If the NodeSet is opened in a generic viewer, remind the audience that generated NodeIds are provisional.

## What the implementation has already found

Release 0.2.0 exists because someone built 0.1.0 against the OPC UA .NET Standard stack and worked
through the bin-picking scenario of the Robotics-Vision Addendum. Issues #66 to #71 came out of it:

- **All 13 Methods with arguments were uncallable.** `InputArguments` and `OutputArguments` were
  qualified into the model's own namespace instead of namespace 0, so a stack resolving a Method's
  signature found none and refused every call with `Bad_TooManyArguments`. The implementation's own
  unit tests passed throughout, because they call the handler delegates directly; only an
  end-to-end session surfaced it.
- **A depth sensor could not state its depth image shape**, so implementations were carrying it in
  vendor-private Properties — the exact failure the model exists to prevent.
- **An empty observation was inexpressible**, so an agent that had emptied the bin could not report
  it, and a false positive could not be retracted.

This is the honest version of "what it would take to make this runnable": part of it is done, and
doing it is what found the defects above.

## What is still missing to make it runnable

- The committed branch head compiles clean.
- The bin-picking client's perception loop correlates a `RunInference` result with a published result node.
- A `run-demo.ps1` here, once both hold.

## Links

- [Vision draft](../../../metaverse-specs/vision/OPC-UA-Vision.md)
- [Vision changelog](../../../metaverse-specs/vision/CHANGELOG.md)
- [Vision research report](../../../metaverse-specs/vision/OPC-UA-Vision-Research.md)
- [Vision NodeSet](../../../metaverse-specs/vision/Opc.Ua.Vision.NodeSet2.xml)
- [Data Channels draft](../../../core-specs/data-channels/OPC-UA-Data-Channels.md)
- [AI Model Management draft](../../../metaverse-specs/ai-model-management/OPC-UA-AI-Model-Management.md)
