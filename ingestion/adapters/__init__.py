from ingestion.adapters.direct_listing import DirectJSONAPIAdapter, HTMLListingAdapter
from ingestion.adapters.feed_parser import FeedParserAdapter
from ingestion.adapters.generated_feed import RSSBridgeAdapter, RSSHubAdapter
from ingestion.adapters.types import (
    AcquisitionAdapterError,
    AdapterRetrieval,
    SourceAcquisitionAdapter,
)

__all__ = [
    "AcquisitionAdapterError",
    "AdapterRetrieval",
    "DirectJSONAPIAdapter",
    "FeedParserAdapter",
    "HTMLListingAdapter",
    "RSSBridgeAdapter",
    "RSSHubAdapter",
    "SourceAcquisitionAdapter",
]
