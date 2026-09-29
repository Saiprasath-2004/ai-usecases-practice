ATS Backend End-to-End Flow Testing

Purpose

Clean-start manual API test plan for the current ATS backend. Use this
after deleting/recreating ats_business.db.

Flow:

Health
  ↓
Create JD file
  ↓
Create Job
  ↓
Create Applications
  ↓
Evaluate Candidates
  ↓
LangGraph HITL
  ↓
Recruiter Review
  ├── Hold
  ├── Reject
  ├── Move to Review
  ├── Get More Details → Candidate Reply → Rescore
  └── Schedule Interview
          ↓
      Scheduling Intent
          ↓
      Calendar Availability
          ↓
      Slot Selection
          ↓
      PendingInvitation
          ↓
      Candidate Invitation
          ↓
      Scheduled + Invitation SENT
          ↓
      Candidate Response
          ├── ACCEPTED
          └── DECLINED

0. Clean Start

Delete/recreate:

ats_business.db

Do not delete:

actions_outbox.sqlite

Then start the backend.

1. Start Backend

uvicorn ats_agent.main:app --reload

Open:

http://127.0.0.1:8000/docs

2. Health Check

GET /

Expected:

{
  "message": "ATS Recruiter Agent API is online.",
  "docs": "/docs"
}

3. Create the JD File

Create:

jd.txt

Content:

Senior Full Stack Developer

We are looking for a Full Stack Developer to design and build modern web applications.

Responsibilities:
- Design and build React applications.
- Build backend APIs using Python and FastAPI.
- Design and maintain PostgreSQL database structures.
- Develop responsive user interfaces.
- Integrate frontend applications with backend services.
- Participate in code reviews.
- Troubleshoot application issues.
- Work in an Agile development environment.

Required Skills:
- Python
- FastAPI
- React
- TypeScript
- JavaScript
- PostgreSQL
- SQL
- REST APIs
- Git

Preferred Skills:
- Docker
- AWS
- CI/CD
- Redis

Experience:
2 to 5 years of relevant software development experience.

Keywords:
Full Stack Development
Web Applications
REST APIs
Database
Agile
Code Reviews
Cloud
CI/CD

Make sure the file path used by the job actually exists. For example:

jd.txt

4. Create Job

Use the current job-creation endpoint exposed by Swagger. If it is
POST /jobs, use:

{
  "title": "Senior Full Stack Developer",
  "department": "Engineering",
  "location": "Chennai, India",
  "employment_type": "Full-time",
  "job_description_text": "We are looking for a Full Stack Developer to design and build modern web applications using React, TypeScript, Python, FastAPI and PostgreSQL.",
  "job_description_source": "jd.txt",
  "required_skills": "["Python", "FastAPI", "React", "TypeScript", "JavaScript", "PostgreSQL", "SQL", "REST APIs", "Git"]"
}

If your current project uses:

POST /jobs/seed/default

use that instead and record the returned ID.

Record:

JOB_ID = <returned job id>

5. Verify Job Routes

List

GET /jobs

Details

GET /jobs/{JOB_ID}

Verify:

title
department
location
employment_type
job_description_source
required_skills
evaluation_status

Expected:

evaluation_status = Active

Job applications

GET /jobs/{JOB_ID}/applications

Expected initially:

[]

6. Create Test Applications

Create at least four candidates so every workflow path can be tested
independently.

Use the actual resume files available in the project. The current test
setup has used:

input/resume_1.pdf
input/resume_2.pdf
input/resume_3.pdf

Candidate 1 --- Interview

POST /applications

{
  "job_requisition_id": 1,
  "candidate_name": "Interview Test Candidate",
  "candidate_email": "interview@example.com",
  "resume_path": "input/resume_1.pdf"
}

Record:

APPLICATION_INTERVIEW = <returned application_id>

Candidate 2 --- Hold

{
  "job_requisition_id": 1,
  "candidate_name": "Hold Test Candidate",
  "candidate_email": "hold@example.com",
  "resume_path": "input/resume_2.pdf"
}

Record:

APPLICATION_HOLD = <returned application_id>

Candidate 3 --- Reject

{
  "job_requisition_id": 1,
  "candidate_name": "Reject Test Candidate",
  "candidate_email": "reject@example.com",
  "resume_path": "input/resume_2.pdf"
}

Record:

APPLICATION_REJECT = <returned application_id>

Candidate 4 --- Follow-up

{
  "job_requisition_id": 1,
  "candidate_name": "Followup Test Candidate",
  "candidate_email": "followup@example.com",
  "resume_path": "input/resume_3.pdf"
}

Record:

APPLICATION_FOLLOWUP = <returned application_id>

The follow-up candidate must have at least one missing skill after
evaluation.

7. Verify Applications

GET /applications/job/{JOB_ID}

Expected initial state:

pipeline_stage = Needs Review
evaluation_status = Pending

Individual application:

GET /applications/{APPLICATION_ID}

8. Evaluate Applications

For each application:

POST /applications/{APPLICATION_ID}/evaluate

Expected flow:

Application
    ↓
Load JD
    ↓
Load Resume
    ↓
Extract JD Requirements
    ↓
Extract Resume Profile
    ↓
Match Requirements
    ↓
Calculate Deterministic Score
    ↓
AI Recommendation
    ↓
Build Evidence
    ↓
Build Narrative
    ↓
HITL Human Review

Verify:

evaluation_status
pipeline_stage
overall_score
thread_id
run_id
run_status

The graph should reach the human-review state.

9. Verify Evaluation Persistence

GET /applications/{APPLICATION_ID}

Check:

overall_score
score_breakdown
matched_skills
missing_skills
strengths
gaps
responsibilities_matched
responsibilities_missing
experience_result
thread_id
current_evaluation_run_id
evaluation_status
pipeline_stage

Important:

AI recommendation != final recruiter decision

10. Recruiter Review --- HOLD

Use APPLICATION_HOLD.

POST /applications/{APPLICATION_ID}/review

{
  "decision": "Hold",
  "comments": "Keep this candidate on hold for further recruiter review."
}

Expected:

pipeline_stage = On Hold

11. Recruiter Review --- REJECT

Use APPLICATION_REJECT.

POST /applications/{APPLICATION_ID}/review

{
  "decision": "Reject",
  "comments": "Candidate does not meet the current requirements."
}

Expected:

pipeline_stage = Rejected
communication.status = SENT

Verify the mock rejection email in the backend console.

12. Recruiter Review --- MOVE TO REVIEW

Use another evaluated application.

POST /applications/{APPLICATION_ID}/review

{
  "decision": "Move to Review",
  "comments": "Needs additional recruiter review before a final decision."
}

Expected:

pipeline_stage = Needs Review

13. Recruiter Review --- GET MORE DETAILS

Use APPLICATION_FOLLOWUP.

First:

GET /applications/{APPLICATION_FOLLOWUP}

Confirm:

missing_skills

contains at least one skill.

Then:

POST /applications/{APPLICATION_FOLLOWUP}/review

{
  "decision": "Get More Details",
  "comments": "Ask the candidate to clarify their experience with the missing technical skills."
}

Expected:

LangGraph generates follow-up questions
↓
Graph pauses at candidate follow-up
↓
Mock candidate email is sent

Verify:

communication.action_id
communication.status = SENT

14. Candidate Follow-up Reply

POST /applications/{APPLICATION_FOLLOWUP}/followup-reply

Example:

{
  "candidate_reply": "I have professional experience using Power BI to build dashboards and reports. I have also used Maven for dependency management in Java projects. I have some exposure to Jenkins and CI/CD pipelines through my internship."
}

Expected:

Candidate Reply
      ↓
Extract confirmations
      ↓
Update matches
      ↓
Recalculate score
      ↓
Rebuild evidence
      ↓
Rebuild narrative
      ↓
Persist latest snapshot
      ↓
Return to recruiter review

Verify:

confirmed skills → matched_skills
confirmed skills removed from missing_skills
remaining missing skills remain missing
overall_score updated
score_breakdown updated
strengths updated
gaps updated

Then:

GET /applications/{APPLICATION_FOLLOWUP}

Verify the updated snapshot is persisted.

15. Calendar --- Default Weekday

Use a future Monday:

2026-09-28

Default availability:

Monday-Friday
10:00-17:00

Request:

GET /calendar/slots

Parameters:

recruiter_id=recruiter_1
target_date=2026-09-28
duration_minutes=60

Expected slots are inside:

10:00-17:00

Typical 30-minute slots:

10:00-11:00
10:30-11:30
11:00-12:00
...
16:00-17:00

16. Calendar --- Weekend

Use:

2026-09-26

Saturday.

GET /calendar/slots

Parameters:

recruiter_id=recruiter_1
target_date=2026-09-26
duration_minutes=60

Expected:

{
  "slots": []
}

17. Multiple Availability Windows

Configure Monday:

10:00-12:00
14:00-17:00

Window 1

POST /calendar/availability

{
  "recruiter_id": "recruiter_1",
  "day_of_week": 0,
  "start_time": "10:00:00",
  "end_time": "12:00:00",
  "active": true
}

Window 2

POST /calendar/availability

{
  "recruiter_id": "recruiter_1",
  "day_of_week": 0,
  "start_time": "14:00:00",
  "end_time": "17:00:00",
  "active": true
}

Verify:

GET /calendar/availability?recruiter_id=recruiter_1

Expected:

10:00-12:00
14:00-17:00

Then:

GET /calendar/slots

with:

target_date=2026-09-28
duration_minutes=60

Expected valid slots include:

10:00-11:00
10:30-11:30
11:00-12:00

14:00-15:00
14:30-15:30
15:00-16:00
15:30-16:30
16:00-17:00

No slot may cross:

12:00-14:00

18. Partial Calendar Block

POST /calendar/blocks

{
  "recruiter_id": "recruiter_1",
  "start_at": "2026-09-28T14:00:00",
  "end_at": "2026-09-28T15:00:00",
  "all_day": false,
  "reason": "Internal meeting"
}

Record:

BLOCK_ID = <returned block id>

Regenerate slots.

Expected:

14:00-15:00 unavailable

Other valid slots remain available.

19. Full-Day Calendar Block

POST /calendar/blocks/full-day

{
  "recruiter_id": "recruiter_1",
  "target_date": "2026-09-29",
  "reason": "Leave"
}

Then:

GET /calendar/slots

with:

target_date=2026-09-29
duration_minutes=60

Expected:

{
  "slots": []
}

Remove the block afterward using the current Swagger delete route and
returned block ID.

20. Requested Slot Validation

For availability:

10:00-12:00
14:00-17:00

Requested slot   Expected

10:00-11:00      PASS
11:00-12:00      PASS
12:00-13:00      FAIL
13:00-14:00      FAIL
14:00-15:00      PASS
16:00-17:00      PASS
11:30-12:30      FAIL

21. Negative Calendar Tests

Invalid duration

Test:

duration_minutes = 0
duration_minutes = -30

Expected:

Validation failure

Invalid availability

{
  "recruiter_id": "recruiter_1",
  "day_of_week": 0,
  "start_time": "15:00:00",
  "end_time": "14:00:00",
  "active": true
}

Expected:

Validation error

Overlapping availability

Existing:

10:00-12:00

Try:

11:00-13:00

Expected:

409 Conflict

Outside availability

Request:

08:00-09:00

Expected:

Requested interview is outside recruiter availability.

Block conflict

Block:

14:00-15:00

Request:

14:00-15:00

Expected:

Requested interview overlaps a blocked period.

22. Natural-Language Interview Scheduling

Use:

APPLICATION_INTERVIEW

Ensure a valid future calendar slot exists.

Request:

POST /applications/{APPLICATION_INTERVIEW}/review

{
  "decision": "Schedule Interview",
  "comments": "Schedule the interview next Tuesday afternoon for 60 minutes."
}

Expected flow:

Recruiter comment
      ↓
LLM parses SchedulingIntent
      ↓
Deterministic slot selector
      ↓
Available slot
      ↓
book_interview()

The LLM must not choose or book the actual calendar slot.

23. Verify Interview Invitation Lifecycle

After successful scheduling, verify the response contains:

interview.status = Scheduled
interview.invitation_status = SENT
interview.candidate_response = AWAITING_RESPONSE
communication.status = SENT

Expected lifecycle:

PendingInvitation
      ↓
Invitation successfully sent
      ↓
Scheduled
      ↓
Invitation = SENT
      ↓
Candidate = AWAITING_RESPONSE

Verify the mock invitation email in the backend console.

24. Candidate Accepts Interview

Use:

POST /applications/{APPLICATION_INTERVIEW}/interview/respond

Body:

{
  "response": "ACCEPTED"
}

Expected:

status = Scheduled
invitation_status = SENT
candidate_response = ACCEPTED
candidate_responded_at = <timestamp>

This is the recruiter-visible state indicating that the candidate
accepted the interview.

25. Duplicate Candidate Response

Call the same endpoint again:

{
  "response": "DECLINED"
}

Expected:

409 Conflict

The previous:

ACCEPTED

must not be overwritten.

26. Candidate Declines Interview

Use another independently scheduled test interview.

POST /applications/{APPLICATION_ID}/interview/respond

{
  "response": "DECLINED"
}

Expected:

candidate_response = DECLINED
candidate_responded_at = <timestamp>

27. Invalid Candidate Response

{
  "response": "MAYBE"
}

Expected:

400 Bad Request

Valid responses are only:

ACCEPTED
DECLINED

28. Candidate Cannot Respond Before Invitation Is Sent

For an interview whose invitation is not successfully sent, candidate
response must be rejected.

Expected:

409 Conflict

29. Interview Double Booking

If an interview exists:

14:00-15:00

attempt:

14:30-15:30

for the same recruiter.

Expected:

Requested interview overlaps an existing interview.

The second interview must not be booked.

30. Explicit Hold Endpoint

POST /applications/{APPLICATION_ID}/hold

Expected:

pipeline_stage = On Hold

31. Explicit Reject Endpoint

POST /applications/{APPLICATION_ID}/reject

Expected:

pipeline_stage = Rejected
communication.status = SENT

Verify the mock rejection email.

32. Generic Application Action

POST /applications/{APPLICATION_ID}/actions

Example:

{
  "action_type": "HOLD",
  "note": "Keep candidate for later review."
}

Expected:

pipeline_stage = On Hold

Also test:

{
  "action_type": "MOVE_TO_REVIEW",
  "note": "Requires recruiter review."
}

Expected:

pipeline_stage = Needs Review

Do not use the generic action endpoint for interview scheduling.

33. Complete Interview State Machine

                  ┌─────────────────────┐
                  │ PendingInvitation   │
                  │ invitation=PENDING  │
                  └──────────┬──────────┘
                             │
                      invitation sent
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Scheduled           │
                  │ invitation=SENT     │
                  │ candidate=AWAITING  │
                  └──────────┬──────────┘
                             │
                    candidate response
                         ┌───┴────┐
                         │        │
                         ▼        ▼
                     ACCEPTED  DECLINED

The recruiter must be able to distinguish:

Interview scheduled?
Invitation sent?
Candidate accepted?

These are separate states.

34. Final End-to-End Run

Run this sequence after the clean database reset:

1. Delete/recreate ats_business.db
2. Start backend
3. Health check
4. Create jd.txt
5. Create Job
6. List Jobs
7. Get Job
8. Create 4 Applications
9. List Applications
10. Get Application
11. Evaluate Applications
12. Verify evaluation snapshot
13. HITL recruiter review
14. HOLD
15. REJECT
16. MOVE TO REVIEW
17. GET MORE DETAILS
18. Candidate follow-up reply
19. Rescore
20. Verify updated persistence
21. Calendar availability
22. Calendar slots
23. Calendar block
24. Natural-language scheduling
25. Interview PendingInvitation
26. Invitation SENT
27. Interview Scheduled
28. Candidate AWAITING_RESPONSE
29. Candidate ACCEPTED
30. Candidate DECLINED using another interview
31. Duplicate response rejected
32. Invalid response rejected
33. Double booking rejected

35. Test Variables

Keep these IDs while testing:

JOB_ID =

APPLICATION_INTERVIEW =

APPLICATION_HOLD =

APPLICATION_REJECT =

APPLICATION_FOLLOWUP =

BLOCK_ID =

36. Final Checklist

[ ] ats_business.db recreated
[ ] Backend starts
[ ] Health check
[ ] JD file created
[ ] Job created
[ ] Job listing
[ ] Job details
[ ] Job applications
[ ] Application creation
[ ] Application listing
[ ] Application details

[ ] JD extraction
[ ] Resume extraction
[ ] Requirement matching
[ ] Deterministic scoring
[ ] AI recommendation
[ ] Evidence
[ ] Narrative
[ ] EvaluationRun
[ ] EvaluationResult
[ ] Persistent thread
[ ] HITL pause

[ ] Recruiter Hold
[ ] Recruiter Reject
[ ] Rejection email
[ ] Move to Review
[ ] Get More Details
[ ] Follow-up questions
[ ] Follow-up email
[ ] Candidate follow-up reply
[ ] Rescoring
[ ] Updated evidence
[ ] Updated persistence

[ ] Default weekday availability
[ ] Weekend rejection
[ ] Multiple availability windows
[ ] Partial calendar block
[ ] Full-day calendar block
[ ] Slot generation
[ ] Requested slot validation
[ ] Invalid duration
[ ] Invalid availability
[ ] Overlapping availability
[ ] Outside availability
[ ] Block conflict
[ ] Existing interview conflict

[ ] Natural-language scheduling
[ ] Interview PendingInvitation
[ ] Invitation SENT
[ ] Interview Scheduled
[ ] Candidate AWAITING_RESPONSE
[ ] Candidate ACCEPTED
[ ] Candidate DECLINED
[ ] Duplicate response rejected
[ ] Invalid response rejected
[ ] Double booking rejected

[ ] Explicit Hold endpoint
[ ] Explicit Reject endpoint
[ ] Generic application action

37. Current Scope --- Future Production Work

- Real email provider
- Real Google/Microsoft calendar integration
- Real meeting provider
- Secure candidate response tokens/links
- Interview reschedule
- Interview cancellation
- Invitation retry endpoint
- Production authentication/authorization
- PostgreSQL migration
- Alembic production migrations
- Production outbox/worker