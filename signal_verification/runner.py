from tilebox.workflows import Runner

from .tasks import VerifySignal

runner = Runner(tasks=[VerifySignal])
