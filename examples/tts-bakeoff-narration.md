---
lectra_schema: "1.0"
title: Lectra Local TTS Bake-off
author: Lectra
language: en-US
target_duration_minutes: 3
style: academic-presentation
default_pace: normal
default_tone: explanatory
---

<!-- slide: 1 -->

Good afternoon everyone.

Today I want to use a simple clinical example to explain what we should expect from a trustworthy prediction model.

<!-- pause: medium -->

Suppose we build a model that estimates the five-year risk of stroke from routinely collected health data. At first, we may focus on discrimination. For example, imagine that the model reaches an A U R O C of zero point eight two.

That result is useful, but it is not enough.

<!-- slide: 2 -->

The first issue is calibration.

If the model assigns a twenty percent risk to one hundred similar patients, we would like roughly twenty of those patients to experience the outcome. A model can rank patients correctly and still produce probabilities that are systematically too high or too low.

<!-- pause: short -->

This distinction becomes particularly important when a prediction changes a clinical decision.

<!-- tone: serious -->

For example, a poorly calibrated model could move patients across a treatment threshold even when the ranking performance looks excellent.

<!-- slide: 3 -->

<!-- tone: explanatory -->

The second issue is transportability.

Performance at the development hospital does not guarantee performance somewhere else. Differences in patient characteristics, clinical practice, data collection, and prevalence can all change the behavior of the model.

For this reason, external validation should examine more than one summary metric. We may compare discrimination, sensitivity, specificity, positive predictive value, calibration slope, and calibration intercept across sites.

<!-- pause: medium -->

We should also look directly at clinically important subgroups rather than assuming that average performance represents everyone.

<!-- slide: 4 -->

Now consider a more difficult example: predicting deterioration after an acute ischemic stroke.

The model may need to distinguish true neurologic worsening from documentation artifacts, medication changes, or temporary fluctuations. Terms such as thrombolysis, thrombectomy, intracerebral hemorrhage, dysarthria, and hemiparesis also create a useful test of pronunciation fidelity for a speech system.

<!-- tone: reflective -->

The technical metric is therefore only one part of the story. We also need to ask whether clinicians can understand the output, whether uncertainty is communicated honestly, and whether the model remains useful after deployment.

<!-- slide: 5 -->

<!-- tone: explanatory -->

I want to end with three points.

First, high discrimination does not imply good calibration.

Second, internal validation does not establish transportability.

Third, model evaluation should follow the clinical decision that the model is intended to support.

<!-- pause: medium -->

If we keep those three principles in mind, we can move from models that perform well on a retrospective test set toward systems that are more credible in real clinical practice.

Thank you.
