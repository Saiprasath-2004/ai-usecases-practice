ATS Agent — End-to-End Testing Checklist

Purpose

Reusable regression checklist for the ATS Agent. Run the tests in order and mark each item PASS/FAIL.

Main Test Data

application_id = 521d7f85-8b93-4a18-b303-b068c08c0066
candidate_name = Review Candidate
candidate_email = review@example.com
resume_path = input/resume_1.pdf
thread_id = application_b1d6354b57cc4a40ad707ecad7984ba9
recruiter_id = recruiter_1

For clean regression tests, create a fresh Job + Application rather than reusing an old application.

A. Job & Application

A1. Create Job

POST /jobs

{
  "title": "Full Stack Developer",
  "description": "We are looking for a Full Stack Developer with experience in React, Angular, JavaScript, HTML5, CSS3, GitHub, Python, FastAPI, SQL, REST APIs, Agile development, unit testing, and code reviews. The candidate should have 2 to 6 years of software development experience.",
  "department": "Engineering"
}

Expected: job created; save job_id.

Status: [ ] PASS [ ] FAIL

A2. Create Application

POST /applications

{
  "job_requisition_id": "<JOB_ID>",
  "candidate_name": "Test Candidate",
  "candidate_email": "testcandidate@example.com",
  "resume_path": "input/resume_1.pdf"
}

Expected: application created; evaluation_status = Pending; save application_id and thread_id.

Status: [ ] PASS [ ] FAIL

B. Initial Evaluation

B1. Run Evaluation

POST /applications/{application_id}/evaluate

No body.

Expected:

evaluation status returned

pipeline stage returned

score returned

thread ID returned

run ID returned

run status returned

typical state: Completed / Needs Review / Waiting for Review

Status: [ ] PASS [ ] FAIL

B2. Candidate Detail

GET /applications/{application_id}

Verify:

overall_score

score_breakdown

matched_skills

missing_skills

strengths

gaps

responsibilities_matched

responsibilities_missing

experience_result

current_evaluation_run_id

thread_id

Status: [ ] PASS [ ] FAIL

B3. Evaluation History

GET /applications/{application_id}/evaluations

Expected:

EvaluationRun exists

EvaluationResult exists

score, breakdown, evidence, narrative exist

historical run is preserved

Status: [ ] PASS [ ] FAIL

B4. Action History

GET /applications/{application_id}/actions

Fresh application expected:

[]

Status: [ ] PASS [ ] FAIL

C. HITL Follow-up

C1. Get More Details

POST /applications/{application_id}/review

{
  "action_type": "Get More Details",
  "comments": "Ask the candidate to clarify their experience with Power BI, Maven, and Jenkins."
}

Expected:

follow-up workflow starts

candidate questions generated

recruiter action recorded

Status: [ ] PASS [ ] FAIL

C2. Verify Action History

GET /applications/{application_id}/actions

Expected: follow-up-related recruiter action exists.

Status: [ ] PASS [ ] FAIL

C3. Candidate Reply

POST /applications/{application_id}/followup-reply

{
  "candidate_reply": "I have used Power BI to create dashboards and reports for business data. I have worked with Maven for Java dependency management and build automation. I also have experience using Jenkins to automate builds and deployments in a CI/CD environment."
}

Expected:

reply processed

NEW EvaluationRun created

NEW EvaluationResult created

application snapshot updated

candidate returns to recruiter review

Status: [ ] PASS [ ] FAIL

C4. Verify New Evaluation History

GET /applications/{application_id}/evaluations

Expected:

old run preserved

new run exists

current_evaluation_run_id points to newest run

old score/evidence/narrative unchanged

Status: [ ] PASS [ ] FAIL

C5. Verify Application Snapshot

GET /applications/{application_id}

Verify latest score, matched/missing skills, strengths, gaps, responsibilities, experience, and current run ID.

Status: [ ] PASS [ ] FAIL

D. Recruiter Decisions

D1. Hold

{
  "action_type": "Hold",
  "comments": "Keep the candidate on hold for further review."
}

Expected: pipeline_stage = On Hold.

Status: [ ] PASS [ ] FAIL

D2. Move to Review

{
  "action_type": "Move to Review",
  "comments": "Move the candidate back to recruiter review."
}

Expected: pipeline_stage = Needs Review.

Status: [ ] PASS [ ] FAIL

D3. Confirm Rejection

Use a separate test application.

{
  "action_type": "Confirm Rejection",
  "comments": "Reject the candidate after recruiter review."
}

Expected:

pipeline_stage = Rejected

recruiter action recorded

rejection notification/outbox action created

Status: [ ] PASS [ ] FAIL

E. Interview Scheduling

E1. Flexible Scheduling

POST /applications/{application_id}/review

{
  "action_type": "Schedule Interview",
  "comments": "Schedule the candidate next week on any weekday afternoon between 2 PM and 5 PM. Any available 60-minute slot is fine."
}

Expected:

LLM parses scheduling preferences.

Deterministic selector finds a valid slot.

Slot is validated.

Interview is booked.

Invitation is sent.

The LLM must not directly choose/book the database slot.

Status: [ ] PASS [ ] FAIL

E2. Verify Interview

GET /calendar/interviews?recruiter_id=recruiter_1

Expected:

application_id

scheduled_at

duration_minutes

invitation_status

candidate_response

candidate_email

Typical initial lifecycle:

invitation_status = SENT
candidate_response = AWAITING_RESPONSE

Status: [ ] PASS [ ] FAIL

E3. Candidate Accepts

POST /applications/{application_id}/interview-response

{
  "interview_id": 3,
  "response": "ACCEPTED"
}

Expected: candidate_response = ACCEPTED and response timestamp exists.

Status: [ ] PASS [ ] FAIL

E4. Candidate Declines

Use another interview.

{
  "interview_id": 4,
  "response": "DECLINED"
}

Expected: candidate_response = DECLINED.

Status: [ ] PASS [ ] FAIL

F. Interview Edge Cases

F1. Duplicate Response

Send the same ACCEPTED request twice.

Expected:

second request rejected

existing response not overwritten

Status: [ ] PASS [ ] FAIL

F2. Invalid Response

{
  "interview_id": 3,
  "response": "MAYBE"
}

Expected: request rejected; interview unchanged.

Status: [ ] PASS [ ] FAIL

F3. Double Booking

Try booking another interview for the same recruiter and occupied time.

Expected: booking rejected; existing interview unchanged.

Status: [ ] PASS [ ] FAIL

F4. Minimum Notice

Try scheduling less than the configured minimum notice.

Expected: booking rejected.

Status: [ ] PASS [ ] FAIL

F5. Holiday

Try scheduling on a configured public holiday.

Expected: booking rejected.

Status: [ ] PASS [ ] FAIL

F6. Exact Scheduling

{
  "action_type": "Schedule Interview",
  "comments": "Schedule the interview exactly on October 6, 2026 at 3:00 PM for 60 minutes. Do not move it to another time."
}

Expected if unavailable:

do not silently move to another slot

fail or require another recruiter instruction

Status: [ ] PASS [ ] FAIL

G. Evaluation Edge Cases

G1. Invalid Resume

Create:

{
  "job_requisition_id": "<JOB_ID>",
  "candidate_name": "Invalid Resume Candidate",
  "candidate_email": "invalid@example.com",
  "resume_path": "input/nonexistent_resume.pdf"
}

Then:
POST /applications/{application_id}/evaluate

Expected:

evaluation_status = Failed

run_status = Failed

no NoneType crash

failure persisted

Status: [ ] PASS [ ] FAIL

G2. Re-evaluation

Run evaluation again on an already evaluated application.

Expected:

Old EvaluationRun -> preserved
New EvaluationRun -> created
current_evaluation_run_id -> newest run

Status: [ ] PASS [ ] FAIL

H. Full End-to-End Scenario

Run on a fresh application:

Create Job
  -> Create Application
  -> Evaluate
  -> Waiting for Recruiter Review
  -> Get More Details
  -> Candidate Questions
  -> Candidate Reply
  -> New EvaluationRun
  -> New EvaluationResult
  -> Recruiter Review
  -> Schedule Interview
  -> Interview Created
  -> Invitation Sent
  -> Candidate Accepts
  -> Interview Accepted

Status: [ ] PASS [ ] FAIL

I. Final Data Integrity Checks

Application

current_evaluation_run_id -> latest run
overall_score -> latest score
pipeline_stage -> current recruiter stage
thread_id -> persistent

Evaluation History

Every EvaluationRun preserved
Every EvaluationResult preserved
Failed runs preserved
Previous scores not overwritten

Recruiter Actions

Get More Details recorded
Hold recorded
Move to Review recorded
Schedule Interview recorded
Rejection recorded where applicable

Interview

Interview exists
Invitation status correct
Candidate response correct
Candidate response timestamp exists
Duplicate response prevented
Double booking prevented
Minimum notice enforced
Holiday validation enforced

J. Current Verified Tests

Verified during the current development cycle:

Evaluation failure handling — PASS

Evaluation rerun/history behavior — PASS

Recruiter action history — PASS

Follow-up candidate response — PASS

Follow-up creates a new evaluation run — PASS

Historical evaluation remains preserved — PASS

Calendar minimum notice — PASS

Calendar holiday validation — PASS

Calendar next available slot — PASS

Calendar double booking — PASS

Interview accept — PASS

Interview decline — PASS

Duplicate interview response — PASS

Invalid interview response — PASS

Mock email/outbox — PASS

Current history example:

Run 5  -> Waiting for Review -> score 70
Run 9  -> Failed -> sentence_transformers package error
Run 10 -> Waiting for Review -> score 69

Run 10 contains the follow-up evaluation evidence, while Run 5 remains preserved.

K. Regression Test Record

Test Date:
Tester:
Branch:
Commit:
Environment:

Initial Evaluation:       [ ] PASS [ ] FAIL
Evaluation History:      [ ] PASS [ ] FAIL
HITL Review:             [ ] PASS [ ] FAIL
Follow-up Questions:     [ ] PASS [ ] FAIL
Candidate Reply:         [ ] PASS [ ] FAIL
Follow-up Re-evaluation: [ ] PASS [ ] FAIL
Action History:          [ ] PASS [ ] FAIL
Hold:                    [ ] PASS [ ] FAIL
Move to Review:          [ ] PASS [ ] FAIL
Rejection:               [ ] PASS [ ] FAIL
Interview Scheduling:    [ ] PASS [ ] FAIL
Interview Invitation:    [ ] PASS [ ] FAIL
Candidate Accept:        [ ] PASS [ ] FAIL
Candidate Decline:       [ ] PASS [ ] FAIL
Duplicate Response:      [ ] PASS [ ] FAIL
Invalid Response:        [ ] PASS [ ] FAIL
Double Booking:          [ ] PASS [ ] FAIL
Minimum Notice:          [ ] PASS [ ] FAIL
Holiday Validation:      [ ] PASS [ ] FAIL
Exact Scheduling:        [ ] PASS [ ] FAIL
Flexible Scheduling:     [ ] PASS [ ] FAIL
Invalid Resume:          [ ] PASS [ ] FAIL
Re-evaluation:           [ ] PASS [ ] FAIL

Overall:
Notes:
Known Issues: