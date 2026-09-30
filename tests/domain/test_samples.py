from project_scheduler.domain.validation import validate_project
from project_scheduler.samples import SAMPLE_SIZES, generate_sample


def test_samples_are_valid_and_sized():
    for size in SAMPLE_SIZES:
        p = generate_sample(size)
        assert len(p.tasks) == size
        assert validate_project(p) == []


def test_samples_are_deterministic():
    assert generate_sample(100) == generate_sample(100)


def test_samples_contain_milestones():
    assert any(t.duration == 0 for t in generate_sample(1000).tasks)
