# project-scheduler

A desktop project scheduler that computes the **critical path** of a project.

You enter tasks, their durations in working days, and which tasks each one depends on. project-scheduler works out, for every task:

- the earliest and latest start and finish dates;
- the slack, meaning how far the task can slip without delaying the project;
- whether the task is on the critical path.

It also computes the project finish date. It counts only working days, using a calendar of working weekdays and holidays that you can edit.

