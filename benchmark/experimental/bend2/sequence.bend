# Experimental port of the controller's per-slot decision logic.
# This does not yet run campaigns; Python remains the production controller.
import Base

type Policy is Data:
  FirstSuccess{}
  Independent{}

type Outcome is Data:
  Success{}
  Quota{}
  Auth{}
  ContentFilter{}
  OtherFailure{}

type Decision is Data:
  Run{}
  SkipAfterSuccess{}
  LeaveReserved{}

def next(policy: Policy, selected: Bool, stopped: Bool) -> Decision:
  match policy:
    case Independent{}:
      match stopped:
        case True{}:
          LeaveReserved{}
        case False{}:
          Run{}
    case FirstSuccess{}:
      match selected:
        case True{}:
          match stopped:
            case True{}:
              LeaveReserved{}
            case False{}:
              SkipAfterSuccess{}
        case False{}:
          match stopped:
            case True{}:
              LeaveReserved{}
            case False{}:
              Run{}

def stops(outcome: Outcome) -> Bool:
  match outcome:
    case Quota{}:
      True{}
    case Auth{}:
      True{}
    case ContentFilter{}:
      True{}
    case Success{}:
      False{}
    case OtherFailure{}:
      False{}

def label(d: Decision) -> String:
  match d:
    case Run{}:
      "run"
    case SkipAfterSuccess{}:
      "skip"
    case LeaveReserved{}:
      "reserved"

def main() -> IO(Unit):
  do IO<Unit>:
    a : Unit <- IO.print(label(next(FirstSuccess{}, False{}, False{})))
    b : Unit <- IO.print(label(next(FirstSuccess{}, True{}, False{})))
    c : Unit <- IO.print(label(next(Independent{}, True{}, False{})))
    d : Unit <- IO.print(label(next(Independent{}, False{}, True{})))
    e : Unit <- IO.print(Bool.show(stops(Quota{})))
    f : Unit <- IO.print(Bool.show(stops(ContentFilter{})))
    IO.print(Bool.show(stops(OtherFailure{})))
