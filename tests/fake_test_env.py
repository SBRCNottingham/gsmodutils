"""
Script for creating a fake test env in a temp folder, this will return the temp folder path
that the project is in.
This is useful for debugging more complex things that can be done in pydbg alone
"""
from helpers.tutils import FakeProjectContext

if __name__ == "__main__":
    ctx = FakeProjectContext()
    ctx.__enter__()
    ctx.add_fake_conditions()
    ctx.add_fake_designs()
    ctx.add_fake_tests()

    print("Project created in {}\nThis will not be automatically deleted (unless you reboot)".format(ctx.path))
