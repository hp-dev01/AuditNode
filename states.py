from enum import Enum

class Status(str, Enum):
    SUBMITTED = 'Submitted'
    TIER_1_REVIEW = 'Tier 1 review'
    TIER_2_REVIEW = 'Tier 2 review'
    TIER_3_REVIEW = 'Tier 3 review'
    RESOLVED = 'Resolved'

ALLOWED_TRANSITIONS = {
    Status.SUBMITTED: [Status.TIER_1_REVIEW],
    Status.TIER_1_REVIEW: [Status.RESOLVED, Status.TIER_2_REVIEW],
    Status.TIER_2_REVIEW: [Status.RESOLVED, Status.TIER_3_REVIEW],
    Status.TIER_3_REVIEW: [Status.RESOLVED],
    Status.RESOLVED: [],
}
    