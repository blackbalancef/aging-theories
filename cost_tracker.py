from dataclasses import dataclass, field
from typing import List
from loguru import logger


@dataclass
class CostInfo:
    """Information about a single API call costs"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    model: str
    
    def __str__(self) -> str:
        return (
            f"Tokens: {self.input_tokens} in + {self.output_tokens} out = {self.total_tokens} total | "
            f"Cost: ${self.input_cost_usd:.6f} + ${self.output_cost_usd:.6f} = ${self.total_cost_usd:.6f}"
        )


@dataclass
class CostTracker:
    """Track cumulative costs across multiple API calls"""
    calls: List[CostInfo] = field(default_factory=list)
    
    def add_call(self, cost_info: CostInfo) -> None:
        """
        Add a new API call cost to the tracker
        
        Args:
            cost_info: Cost information for the API call
        """
        self.calls.append(cost_info)
        logger.debug(f"Added cost: {cost_info}")
    
    @property
    def total_input_tokens(self) -> int:
        """Total input tokens across all calls"""
        return sum(call.input_tokens for call in self.calls)
    
    @property
    def total_output_tokens(self) -> int:
        """Total output tokens across all calls"""
        return sum(call.output_tokens for call in self.calls)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output) across all calls"""
        return sum(call.total_tokens for call in self.calls)
    
    @property
    def total_cost_usd(self) -> float:
        """Total cost in USD across all calls"""
        return sum(call.total_cost_usd for call in self.calls)
    
    @property
    def total_input_cost_usd(self) -> float:
        """Total input cost in USD across all calls"""
        return sum(call.input_cost_usd for call in self.calls)
    
    @property
    def total_output_cost_usd(self) -> float:
        """Total output cost in USD across all calls"""
        return sum(call.output_cost_usd for call in self.calls)
    
    @property
    def call_count(self) -> int:
        """Number of API calls tracked"""
        return len(self.calls)
    
    def get_summary(self) -> dict:
        """
        Get a summary of all costs
        
        Returns:
            Dictionary with cost summary
        """
        return {
            "total_calls": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_input_cost_usd": self.total_input_cost_usd,
            "total_output_cost_usd": self.total_output_cost_usd,
            "total_cost_usd": self.total_cost_usd,
            "average_cost_per_call_usd": self.total_cost_usd / self.call_count if self.call_count > 0 else 0.0,
        }
    
    def print_summary(self) -> None:
        """Print a formatted summary of all costs"""
        logger.info("=" * 80)
        logger.info("💰 COST TRACKER SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total API calls: {self.call_count}")
        logger.info(f"Total input tokens: {self.total_input_tokens:,}")
        logger.info(f"Total output tokens: {self.total_output_tokens:,}")
        logger.info(f"Total tokens: {self.total_tokens:,}")
        logger.info("-" * 80)
        logger.info(f"Total input cost: ${self.total_input_cost_usd:.6f}")
        logger.info(f"Total output cost: ${self.total_output_cost_usd:.6f}")
        logger.info(f"Total cost: ${self.total_cost_usd:.6f}")
        
        if self.call_count > 0:
            avg_cost = self.total_cost_usd / self.call_count
            logger.info(f"Average cost per call: ${avg_cost:.6f}")
        
        logger.info("=" * 80)
        
        # Show breakdown by model if multiple models used
        models_used = set(call.model for call in self.calls)
        if len(models_used) > 1:
            logger.info("Cost breakdown by model:")
            for model in models_used:
                model_calls = [call for call in self.calls if call.model == model]
                model_cost = sum(call.total_cost_usd for call in model_calls)
                logger.info(f"  {model}: {len(model_calls)} calls, ${model_cost:.6f}")
            logger.info("=" * 80)
    
    def reset(self) -> None:
        """Reset the tracker, clearing all tracked calls"""
        self.calls.clear()
        logger.info("Cost tracker reset")

