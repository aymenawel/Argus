# Product

<!-- impeccable:product-schema 1 -->

<!-- Written Nov 3, 2026 from docs/knowledge-base (00, 13, 15) and Aymen's answers in the redesign conversation, without a
separate interview; facts not confirmed by Aymen are marked "assumption". -->

## Platform

web

## Users

Researchers without lab training, students, teachers, small labs and hobby scientists who run an experiment in front of
a webcam or USB microscope and want to know what happened and whether their idea held. They glance at a live run now
and then, or rewatch a finished one. Hackathon judges and voters see it through a read-only public demo (assumption:
on laptops first, phones second).

## Product Purpose

Argus watches an experiment through a camera, measures change in real units with SAM 3.1, writes checked notes,
judges the researcher's hypothesis and suggests the next run: plan, watch, measure, judge, next run. Success is a
person with no lab training understanding what their experiment showed and what to try next.

## Positioning

Self-driving-lab intelligence for anyone with a webcam: every number Argus shows is one it measured, every AI claim is
checked against the data, and anything replayed or drawn by code says so.

## Operating Context

A run is watched live or rewatched later: the camera picture over time, each sample's reading with its ±, events
(a hand at the samples, a threshold crossed), Argus's notes, Ask Argus questions about the moment on screen, then the
verdict and the next-run suggestion on Results. The public link is the same app in a read-only demo mode with two
finished runs (a webcam dye run and a published seed-germination plate).

## Capabilities and Constraints

Next.js + TypeScript web app over a local Python worker; the demo is a static build reading exported run bundles.
Plain words on screen for a high-school reader (D-95). The LLM never computes numbers. Submission deadline Nov 4, 2026,
9 PM ET.

## Brand Commitments

Name Argus, the eye mark (`web/app/icon.svg`, teal `#2dd4bf` iris on ink). Aymen chose a light "clean lab" look as the
default with dark available (Nov 3), inspired by three reference screens he sent: a robotics fleet dashboard, a video
editor and a camera-feed app (light grey canvas, white rounded panels, black selected pills, video hero with overlay
time, thumbnail timeline, feed list).

## Evidence on Hand

Real runs only: the Oct 28 webcam dye run (run_d8f8b410078e) and the Genze seed plate (run_0977e12a8cbb, CC BY 4.0,
credited), their pictures, readings, notes, verdicts, next-run suggestions, timelapses and reels. No testimonials,
press or customers exist; none may be invented.

## Product Principles

1. Every number on screen is a measurement, with its ±.
2. Say what's real: recorded, replayed, drawn by code or AI-written is always labelled.
3. Answer first, details on demand: one question per screen.
4. Words a high-school student understands.
