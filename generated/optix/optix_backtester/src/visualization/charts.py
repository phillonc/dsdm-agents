"""
Visualization tools for backtest results
"""
from typing import List, Dict, Any, Optional
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..models.backtest import BacktestResult, MonteCarloResult

# Set style
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (12, 6)


class BacktestVisualizer:
    """Create visualizations for backtest results"""
    
    def __init__(self, result: BacktestResult):
        self.result = result
    
    def plot_equity_curve(
        self,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Plot equity curve
        
        Args:
            save_path: Optional path to save figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if not self.result.equity_curve:
            return fig
        
        df = pd.DataFrame(self.result.equity_curve)
        
        # Plot equity
        ax.plot(df['timestamp'], df['equity'], label='Total Equity', linewidth=2)
        ax.plot(df['timestamp'], df['cash'], label='Cash', linewidth=1, alpha=0.7)
        
        # Add drawdown shading
        cummax = df['equity'].cummax()
        drawdown = (df['equity'] - cummax) / cummax * 100
        
        ax2 = ax.twinx()
        ax2.fill_between(
            df['timestamp'],
            drawdown,
            0,
            alpha=0.3,
            color='red',
            label='Drawdown %'
        )
        
        ax.set_xlabel('Date')
        ax.set_ylabel('Equity ($)')
        ax2.set_ylabel('Drawdown (%)')
        ax.set_title('Equity Curve and Drawdown')
        ax.legend(loc='upper left')
        ax2.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_returns_distribution(
        self,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot returns distribution"""
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        if not self.result.trades:
            return fig
        
        returns = [t.return_percent for t in self.result.trades]
        
        # Histogram
        ax1.hist(returns, bins=30, alpha=0.7, color='blue', edgecolor='black')
        ax1.axvline(0, color='red', linestyle='--', linewidth=2, label='Break-even')
        ax1.axvline(
            np.mean(returns),
            color='green',
            linestyle='--',
            linewidth=2,
            label=f'Mean: {np.mean(returns):.2f}%'
        )
        ax1.set_xlabel('Return (%)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Trade Returns Distribution')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Q-Q plot
        from scipy import stats
        stats.probplot(returns, dist="norm", plot=ax2)
        ax2.set_title('Q-Q Plot (Normal Distribution)')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_monthly_returns(
        self,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot monthly returns heatmap"""
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        if not self.result.trades:
            return fig
        
        # Create DataFrame with trade dates and returns
        df = pd.DataFrame([
            {
                'date': t.exit_time if t.exit_time else t.entry_time,
                'return': t.return_percent
            }
            for t in self.result.trades
            if t.exit_time
        ])
        
        if df.empty:
            return fig
        
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        
        # Aggregate monthly returns
        monthly = df.groupby(['year', 'month'])['return'].sum().reset_index()
        pivot = monthly.pivot(index='month', columns='year', values='return')
        
        # Plot heatmap
        sns.heatmap(
            pivot,
            annot=True,
            fmt='.1f',
            cmap='RdYlGn',
            center=0,
            ax=ax,
            cbar_kws={'label': 'Return (%)'}
        )
        
        ax.set_title('Monthly Returns Heatmap')
        ax.set_ylabel('Month')
        ax.set_xlabel('Year')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_trade_analysis(
        self,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot trade analysis"""
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        if not self.result.trades:
            return fig
        
        # 1. P&L over time
        df = pd.DataFrame([
            {
                'date': t.exit_time if t.exit_time else t.entry_time,
                'pnl': t.net_pnl
            }
            for t in self.result.trades
        ])
        df = df.sort_values('date')
        df['cumulative_pnl'] = df['pnl'].cumsum()
        
        axes[0, 0].plot(df['date'], df['cumulative_pnl'], linewidth=2)
        axes[0, 0].set_title('Cumulative P&L')
        axes[0, 0].set_xlabel('Date')
        axes[0, 0].set_ylabel('P&L ($)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Win/Loss distribution
        winners = [t.net_pnl for t in self.result.trades if t.is_winner]
        losers = [t.net_pnl for t in self.result.trades if not t.is_winner]
        
        axes[0, 1].hist(
            [winners, losers],
            bins=20,
            label=['Winners', 'Losers'],
            color=['green', 'red'],
            alpha=0.7
        )
        axes[0, 1].set_title('Win/Loss Distribution')
        axes[0, 1].set_xlabel('P&L ($)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Holding period analysis
        holding_periods = [
            t.holding_period_seconds / 3600 
            for t in self.result.trades 
            if t.holding_period_seconds
        ]
        
        if holding_periods:
            axes[1, 0].hist(holding_periods, bins=20, alpha=0.7, color='purple')
            axes[1, 0].set_title('Holding Period Distribution')
            axes[1, 0].set_xlabel('Hours')
            axes[1, 0].set_ylabel('Frequency')
            axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Rolling Sharpe ratio
        if len(self.result.trades) > 20:
            returns = [t.return_percent for t in self.result.trades]
            rolling_sharpe = []
            window = 20
            
            for i in range(window, len(returns)):
                window_returns = returns[i-window:i]
                sharpe = np.mean(window_returns) / np.std(window_returns) if np.std(window_returns) > 0 else 0
                rolling_sharpe.append(sharpe)
            
            axes[1, 1].plot(rolling_sharpe, linewidth=2)
            axes[1, 1].axhline(0, color='red', linestyle='--', alpha=0.5)
            axes[1, 1].set_title(f'Rolling Sharpe Ratio (window={window})')
            axes[1, 1].set_xlabel('Trade Number')
            axes[1, 1].set_ylabel('Sharpe Ratio')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def create_interactive_dashboard(self) -> go.Figure:
        """Create interactive Plotly dashboard"""
        
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Equity Curve',
                'Drawdown',
                'Monthly Returns',
                'Trade P&L',
                'Returns Distribution',
                'Performance Metrics'
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"type": "bar"}, {"type": "scatter"}],
                [{"type": "histogram"}, {"type": "table"}]
            ]
        )
        
        if self.result.equity_curve:
            df = pd.DataFrame(self.result.equity_curve)
            
            # Equity curve
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['equity'],
                    name='Equity',
                    line=dict(color='blue', width=2)
                ),
                row=1, col=1
            )
            
            # Drawdown
            cummax = df['equity'].cummax()
            drawdown = (df['equity'] - cummax) / cummax * 100
            
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=drawdown,
                    name='Drawdown',
                    fill='tozeroy',
                    line=dict(color='red')
                ),
                row=1, col=2
            )
        
        if self.result.trades:
            # Monthly returns
            trade_df = pd.DataFrame([
                {
                    'date': t.exit_time if t.exit_time else t.entry_time,
                    'pnl': t.net_pnl
                }
                for t in self.result.trades
            ])
            
            trade_df['month'] = pd.to_datetime(trade_df['date']).dt.to_period('M')
            monthly_pnl = trade_df.groupby('month')['pnl'].sum()
            
            fig.add_trace(
                go.Bar(
                    x=[str(m) for m in monthly_pnl.index],
                    y=monthly_pnl.values,
                    name='Monthly P&L',
                    marker_color=['green' if x > 0 else 'red' for x in monthly_pnl.values]
                ),
                row=2, col=1
            )
            
            # Cumulative P&L
            trade_df = trade_df.sort_values('date')
            trade_df['cumulative_pnl'] = trade_df['pnl'].cumsum()
            
            fig.add_trace(
                go.Scatter(
                    x=trade_df['date'],
                    y=trade_df['cumulative_pnl'],
                    name='Cumulative P&L',
                    line=dict(color='green', width=2)
                ),
                row=2, col=2
            )
            
            # Returns distribution
            returns = [t.return_percent for t in self.result.trades]
            fig.add_trace(
                go.Histogram(
                    x=returns,
                    name='Returns',
                    nbinsx=30
                ),
                row=3, col=1
            )
        
        # Performance metrics table
        metrics = self.result.performance
        fig.add_trace(
            go.Table(
                header=dict(values=['Metric', 'Value']),
                cells=dict(values=[
                    ['Total Trades', 'Win Rate', 'Total Return', 'Sharpe Ratio', 'Max Drawdown'],
                    [
                        f"{metrics.total_trades}",
                        f"{metrics.win_rate:.2f}%",
                        f"{metrics.total_return:.2f}%",
                        f"{metrics.sharpe_ratio:.2f}",
                        f"{metrics.max_drawdown_percent:.2f}%"
                    ]
                ])
            ),
            row=3, col=2
        )
        
        fig.update_layout(
            height=1200,
            showlegend=True,
            title_text="Backtest Analysis Dashboard"
        )
        
        return fig


class MonteCarloVisualizer:
    """Visualize Monte Carlo simulation results"""
    
    def __init__(self, result: MonteCarloResult):
        self.result = result
    
    def plot_distribution(
        self,
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """Plot Monte Carlo distribution"""
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        returns = [r['total_return'] for r in self.result.iteration_results]
        sharpes = [r['sharpe_ratio'] for r in self.result.iteration_results]
        drawdowns = [r['max_drawdown'] for r in self.result.iteration_results]
        
        # Returns distribution
        axes[0, 0].hist(returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
        axes[0, 0].axvline(
            self.result.mean_return,
            color='red',
            linestyle='--',
            linewidth=2,
            label=f'Mean: {self.result.mean_return:.2f}%'
        )
        axes[0, 0].axvline(
            self.result.return_confidence_95[0],
            color='orange',
            linestyle='--',
            linewidth=1,
            label='95% CI'
        )
        axes[0, 0].axvline(
            self.result.return_confidence_95[1],
            color='orange',
            linestyle='--',
            linewidth=1
        )
        axes[0, 0].set_xlabel('Total Return (%)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Returns Distribution')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Sharpe distribution
        axes[0, 1].hist(sharpes, bins=50, alpha=0.7, color='green', edgecolor='black')
        axes[0, 1].axvline(
            self.result.mean_sharpe,
            color='red',
            linestyle='--',
            linewidth=2,
            label=f'Mean: {self.result.mean_sharpe:.2f}'
        )
        axes[0, 1].set_xlabel('Sharpe Ratio')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].set_title('Sharpe Ratio Distribution')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Drawdown distribution
        axes[1, 0].hist(drawdowns, bins=50, alpha=0.7, color='red', edgecolor='black')
        axes[1, 0].axvline(
            self.result.mean_max_drawdown,
            color='blue',
            linestyle='--',
            linewidth=2,
            label=f'Mean: {self.result.mean_max_drawdown:.2f}%'
        )
        axes[1, 0].set_xlabel('Max Drawdown (%)')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('Max Drawdown Distribution')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Summary statistics
        stats_text = f"""
Monte Carlo Summary
─────────────────────
Iterations: {self.result.iterations}
        
Returns:
  Mean: {self.result.mean_return:.2f}%
  Median: {self.result.median_return:.2f}%
  Std Dev: {self.result.std_return:.2f}%
  95% CI: [{self.result.return_confidence_95[0]:.2f}%, {self.result.return_confidence_95[1]:.2f}%]

Sharpe Ratio:
  Mean: {self.result.mean_sharpe:.2f}
  Median: {self.result.median_sharpe:.2f}

Risk:
  Probability of Profit: {self.result.probability_of_profit * 100:.1f}%
  Probability of Ruin: {self.result.probability_of_ruin * 100:.1f}%
        """
        
        axes[1, 1].text(
            0.1, 0.5,
            stats_text,
            fontsize=10,
            family='monospace',
            verticalalignment='center'
        )
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
