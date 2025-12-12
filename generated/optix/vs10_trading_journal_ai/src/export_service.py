"""
Export Service Module for Trading Journal AI.

This module handles exporting data to various formats including CSV and PDF reports.
"""

import logging
import csv
import os
from datetime import datetime
from typing import List, Dict, Any
from io import StringIO
import tempfile
from sqlalchemy.orm import Session

from .models import Trade, TradeStatus
from .analytics_engine import AnalyticsEngine

logger = logging.getLogger(__name__)

# Try to import PDF libraries
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    PDF_AVAILABLE = True
except ImportError:
    logger.warning("ReportLab not installed. PDF export will not be available.")
    PDF_AVAILABLE = False


class ExportService:
    """
    Service for exporting trading journal data to various formats.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the export service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.analytics = AnalyticsEngine(db_session)
    
    def export_trades_csv(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        output_path: Optional[str] = None
    ) -> str:
        """
        Export trades to CSV file.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            output_path: Optional output file path
            
        Returns:
            Path to created CSV file
        """
        # Get trades
        trades = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.entry_date >= start_date,
            Trade.entry_date <= end_date
        ).order_by(Trade.entry_date).all()
        
        # Create CSV
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix='.csv', prefix='trades_')
            os.close(fd)
        
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = [
                'trade_id', 'symbol', 'direction', 'status',
                'entry_date', 'entry_price', 'quantity',
                'exit_date', 'exit_price',
                'gross_pnl', 'net_pnl', 'pnl_percent',
                'setup_type', 'market_condition', 'sentiment',
                'stop_loss', 'take_profit', 'risk_reward_ratio',
                'entry_commission', 'exit_commission'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for trade in trades:
                writer.writerow({
                    'trade_id': trade.id,
                    'symbol': trade.symbol,
                    'direction': trade.direction.value,
                    'status': trade.status.value,
                    'entry_date': trade.entry_date.isoformat(),
                    'entry_price': trade.entry_price,
                    'quantity': trade.quantity,
                    'exit_date': trade.exit_date.isoformat() if trade.exit_date else '',
                    'exit_price': trade.exit_price or '',
                    'gross_pnl': trade.gross_pnl or '',
                    'net_pnl': trade.net_pnl or '',
                    'pnl_percent': trade.pnl_percent or '',
                    'setup_type': trade.setup_type.value if trade.setup_type else '',
                    'market_condition': trade.market_condition.value if trade.market_condition else '',
                    'sentiment': trade.sentiment.value if trade.sentiment else '',
                    'stop_loss': trade.stop_loss or '',
                    'take_profit': trade.take_profit or '',
                    'risk_reward_ratio': trade.risk_reward_ratio or '',
                    'entry_commission': trade.entry_commission,
                    'exit_commission': trade.exit_commission or ''
                })
        
        logger.info(f"Exported {len(trades)} trades to CSV: {output_path}")
        return output_path
    
    def export_performance_pdf(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        output_path: Optional[str] = None
    ) -> str:
        """
        Export comprehensive performance report as PDF.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            output_path: Optional output file path
            
        Returns:
            Path to created PDF file
        """
        if not PDF_AVAILABLE:
            raise RuntimeError("PDF export requires reportlab package")
        
        # Create PDF
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix='.pdf', prefix='performance_')
            os.close(fd)
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30
        )
        story.append(Paragraph("Trading Performance Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Period
        period_text = f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        story.append(Paragraph(period_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Get performance metrics
        metrics = self.analytics.calculate_performance_metrics(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Summary section
        story.append(Paragraph("Performance Summary", styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Total Trades', str(metrics['total_trades'])],
            ['Winning Trades', str(metrics['winning_trades'])],
            ['Losing Trades', str(metrics['losing_trades'])],
            ['Win Rate', f"{metrics['win_rate']}%"],
            ['Net P&L', f"${metrics['net_pnl']:,.2f}"],
            ['Gross P&L', f"${metrics['gross_pnl']:,.2f}"],
            ['Average P&L', f"${metrics['average_pnl']:.2f}"],
            ['Profit Factor', str(metrics['profit_factor'])],
            ['Expectancy', f"${metrics['expectancy']:.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Risk metrics
        story.append(Paragraph("Risk Metrics", styles['Heading2']))
        risk_data = [
            ['Metric', 'Value'],
            ['Largest Win', f"${metrics['largest_win']:,.2f}"],
            ['Largest Loss', f"${metrics['largest_loss']:,.2f}"],
            ['Max Drawdown', f"${metrics['max_drawdown']:,.2f}"],
            ['Sharpe Ratio', str(metrics['sharpe_ratio'])],
            ['Max Win Streak', str(metrics['max_win_streak'])],
            ['Max Loss Streak', str(metrics['max_loss_streak'])],
            ['Total Commissions', f"${metrics['total_commissions']:,.2f}"]
        ]
        
        risk_table = Table(risk_data, colWidths=[3*inch, 2*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Performance by symbol
        symbol_analysis = self.analytics.analyze_by_symbol(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            min_trades=1
        )
        
        if symbol_analysis['by_symbol']:
            story.append(PageBreak())
            story.append(Paragraph("Performance by Symbol", styles['Heading2']))
            
            symbol_data = [['Symbol', 'Trades', 'Win Rate', 'Net P&L']]
            for symbol, stats in list(symbol_analysis['by_symbol'].items())[:10]:  # Top 10
                symbol_data.append([
                    symbol,
                    str(stats['total_trades']),
                    f"{stats['win_rate']}%",
                    f"${stats['net_pnl']:,.2f}"
                ])
            
            symbol_table = Table(symbol_data, colWidths=[1.5*inch, 1*inch, 1.5*inch, 1.5*inch])
            symbol_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(symbol_table)
        
        # Performance by setup
        setup_analysis = self.analytics.analyze_by_setup_type(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if setup_analysis['by_setup']:
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("Performance by Setup Type", styles['Heading2']))
            
            setup_data = [['Setup', 'Trades', 'Win Rate', 'Net P&L']]
            for setup, stats in setup_analysis['by_setup'].items():
                setup_data.append([
                    setup,
                    str(stats['total_trades']),
                    f"{stats['win_rate']}%",
                    f"${stats['net_pnl']:,.2f}"
                ])
            
            setup_table = Table(setup_data, colWidths=[1.5*inch, 1*inch, 1.5*inch, 1.5*inch])
            setup_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(setup_table)
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        )
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by OPTIX Trading Journal AI"
        story.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"Exported performance report to PDF: {output_path}")
        return output_path
    
    def export_journal_entries_text(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        output_path: Optional[str] = None
    ) -> str:
        """
        Export journal entries to text file.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            output_path: Optional output file path
            
        Returns:
            Path to created text file
        """
        from .journal_service import JournalService
        
        journal_service = JournalService(self.db)
        entries = journal_service.get_user_journal_entries(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )
        
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix='.txt', prefix='journal_')
            os.close(fd)
        
        with open(output_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"Trading Journal Entries\n")
            f.write(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
            f.write("=" * 80 + "\n\n")
            
            for entry in entries:
                f.write(f"Date: {entry.entry_date.strftime('%Y-%m-%d %H:%M:%S')}\n")
                if entry.title:
                    f.write(f"Title: {entry.title}\n")
                if entry.trade_id:
                    f.write(f"Trade ID: {entry.trade_id}\n")
                
                # Mood ratings
                if entry.mood_rating or entry.confidence_level or entry.discipline_rating:
                    f.write("\nRatings:\n")
                    if entry.mood_rating:
                        f.write(f"  Mood: {entry.mood_rating}/10\n")
                    if entry.confidence_level:
                        f.write(f"  Confidence: {entry.confidence_level}/10\n")
                    if entry.discipline_rating:
                        f.write(f"  Discipline: {entry.discipline_rating}/10\n")
                
                # Content
                if entry.content:
                    f.write(f"\nEntry:\n{entry.content}\n")
                
                # Notes
                if entry.notes:
                    f.write(f"\nNotes:\n{entry.notes}\n")
                
                # AI insights
                if entry.ai_suggestions:
                    f.write(f"\nAI Suggestions:\n{entry.ai_suggestions}\n")
                
                f.write("\n" + "-" * 80 + "\n\n")
        
        logger.info(f"Exported {len(entries)} journal entries to text: {output_path}")
        return output_path
    
    def export_all_data(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        output_dir: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Export all data (trades, journal, reports) to multiple files.
        
        Args:
            user_id: User identifier
            start_date: Start date
            end_date: End date
            output_dir: Optional output directory
            
        Returns:
            Dictionary mapping export types to file paths
        """
        if not output_dir:
            output_dir = tempfile.mkdtemp(prefix='trading_journal_export_')
        
        os.makedirs(output_dir, exist_ok=True)
        
        exports = {}
        
        # Export trades CSV
        csv_path = os.path.join(output_dir, 'trades.csv')
        exports['trades_csv'] = self.export_trades_csv(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            output_path=csv_path
        )
        
        # Export performance PDF
        if PDF_AVAILABLE:
            pdf_path = os.path.join(output_dir, 'performance_report.pdf')
            exports['performance_pdf'] = self.export_performance_pdf(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                output_path=pdf_path
            )
        
        # Export journal entries
        journal_path = os.path.join(output_dir, 'journal_entries.txt')
        exports['journal_text'] = self.export_journal_entries_text(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            output_path=journal_path
        )
        
        logger.info(f"Exported all data to directory: {output_dir}")
        return exports
