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

- If someone asks to run it, say plainly that no implementation exists yet.
- If a camera transport question comes up, keep GenICam and GigE Vision below this model; this draft is the semantic and control layer.
- If media transport dominates the conversation, separate the default brokered endpoint from the optional Data Channel facet.
- If the NodeSet is opened in a generic viewer, remind the audience that generated NodeIds are provisional.

## What it would take to make this runnable

- Add an `Opc.Ua.Vision` model project to the stack from the generated Vision NodeSet.
- Implement a sample Vision server with a physical or synthetic camera source.
- Publish at least one media endpoint, plus an optional Data Channel source for in-band clips or stream fragments.
- Implement an inference pipeline that points to a real AI Model Management deployment.
- Publish a standard detection or inspection result with frame, calibration and model provenance.
- Add a client walkthrough that browses `Server/Vision/Sensors`, opens media, reads results and submits feedback.
- Add integration tests proving the same client works against a simulated and physical sensor shape.

## Links

- [Vision draft](../../../metaverse-specs/vision/OPC-UA-Vision.md)
- [Vision research report](../../../metaverse-specs/vision/OPC-UA-Vision-Research.md)
- [Vision NodeSet](../../../metaverse-specs/vision/Opc.Ua.Vision.NodeSet2.xml)
- [Data Channels draft](../../../core-specs/data-channels/OPC-UA-Data-Channels.md)
- [AI Model Management draft](../../../metaverse-specs/ai-model-management/OPC-UA-AI-Model-Management.md)
