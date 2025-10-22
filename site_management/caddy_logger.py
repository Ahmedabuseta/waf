"""
Comprehensive logging system for Caddy site management
Provides per-site logging and centralized operation tracking
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import json
from django.conf import settings


class CaddyLogger:
    """Centralized logging for Caddy operations with per-site logs"""

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            # Use Django setting if available, otherwise fallback to project-relative path
            try:
                log_dir = settings.CADDY_LOG_DIR
            except (ImportError, AttributeError):
                # Fallback for when Django isn't fully initialized or settings don't exist
                log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'caddy-manager')

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        self.sites_log_dir = self.log_dir / "sites"
        self.operations_log_dir = self.log_dir / "operations"
        self.certificates_log_dir = self.log_dir / "certificates"

        for dir_path in [self.sites_log_dir, self.operations_log_dir, self.certificates_log_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Setup main logger
        self.main_logger = self._setup_main_logger()

        # Site-specific loggers cache
        self._site_loggers = {}

    def _setup_main_logger(self) -> logging.Logger:
        """Setup main operations logger"""
        logger = logging.getLogger('caddy_manager')
        logger.setLevel(logging.INFO)

        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # File handler
        log_file = self.operations_log_dir / "caddy_operations.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def get_site_logger(self, domain: str) -> logging.Logger:
        """Get or create logger for specific site"""
        if domain not in self._site_loggers:
            logger = logging.Logger(f'site_{domain}')
            logger.setLevel(logging.INFO)

            # Site-specific log file
            log_file = self.sites_log_dir / f"{domain}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)

            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            self._site_loggers[domain] = logger

        return self._site_loggers[domain]

    def log_site_operation(self, domain: str, operation: str, details: Dict, success: bool = True):
        """Log site-specific operation"""
        site_logger = self.get_site_logger(domain)
        main_logger = self.main_logger

        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILED"

        # Format message
        message = f"{operation.upper()} - {status}"
        if details:
            details_str = json.dumps(details, indent=2)
            message += f"\nDetails: {details_str}"

        # Log to both site-specific and main logger
        site_logger.log(level, message)
        main_logger.log(level, f"[{domain}] {message}")

        # Write operation summary
        self._write_operation_summary(domain, operation, details, success)

    def log_certificate_operation(self, domain: str, operation: str, cert_info: Dict, success: bool = True):
        """Log certificate-related operations"""
        cert_logger = logging.getLogger('caddy_certificates')
        cert_logger.setLevel(logging.INFO)

        if not cert_logger.handlers:
            log_file = self.certificates_log_dir / "certificate_operations.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)

            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            cert_logger.addHandler(file_handler)

        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILED"

        message = f"[{domain}] {operation.upper()} - {status}"
        if cert_info:
            cert_details = json.dumps(cert_info, indent=2)
            message += f"\nCertificate Info: {cert_details}"

        cert_logger.log(level, message)
        self.main_logger.log(level, f"CERT: {message}")

        # Also log to site-specific logger
        site_logger = self.get_site_logger(domain)
        site_logger.log(level, f"CERTIFICATE {operation.upper()} - {status}")

    def log_configuration_change(self, domain: str, old_config: Optional[str], new_config: str, success: bool = True):
        """Log configuration changes with diff tracking"""
        site_logger = self.get_site_logger(domain)

        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILED"

        message = f"CONFIG_UPDATE - {status}"

        # Save configuration snapshots
        config_dir = self.sites_log_dir / domain / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save new config
        new_config_file = config_dir / f"config_{timestamp}.caddy"
        with open(new_config_file, 'w') as f:
            f.write(new_config)

        # Save old config if provided
        if old_config:
            old_config_file = config_dir / f"config_{timestamp}_old.caddy"
            with open(old_config_file, 'w') as f:
                f.write(old_config)

            message += f"\nConfig files saved: {new_config_file.name}, {old_config_file.name}"
        else:
            message += f"\nConfig file saved: {new_config_file.name}"

        site_logger.log(level, message)
        self.main_logger.log(level, f"[{domain}] {message}")

    def log_error(self, domain: str, error_type: str, error_message: str, details: Optional[Dict] = None):
        """Log errors with detailed information"""
        site_logger = self.get_site_logger(domain)

        message = f"ERROR - {error_type}: {error_message}"
        if details:
            details_str = json.dumps(details, indent=2)
            message += f"\nError Details: {details_str}"

        site_logger.error(message)
        self.main_logger.error(f"[{domain}] {message}")

        # Write error summary for monitoring
        error_file = self.sites_log_dir / domain / "errors.json"
        error_file.parent.mkdir(parents=True, exist_ok=True)

        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": error_message,
            "details": details or {}
        }

        # Append to error log
        errors = []
        if error_file.exists():
            try:
                with open(error_file, 'r') as f:
                    errors = json.load(f)
            except:
                errors = []

        errors.append(error_entry)

        # Keep only last 100 errors
        errors = errors[-100:]

        with open(error_file, 'w') as f:
            json.dump(errors, f, indent=2)

    def log_reload(self, success: bool, duration: Optional[float] = None, output: Optional[str] = None):
        """Log Caddy reload operations"""
        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILED"

        message = f"CADDY_RELOAD - {status}"
        if duration:
            message += f" (took {duration:.2f}s)"
        if output:
            message += f"\nOutput: {output}"

        self.main_logger.log(level, message)

    def _write_operation_summary(self, domain: str, operation: str, details: Dict, success: bool):
        """Write operation summary for monitoring and reporting"""
        summary_file = self.sites_log_dir / domain / "operations_summary.json"
        summary_file.parent.mkdir(parents=True, exist_ok=True)

        operation_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "success": success,
            "details": details
        }

        # Read existing summaries
        summaries = []
        if summary_file.exists():
            try:
                with open(summary_file, 'r') as f:
                    summaries = json.load(f)
            except:
                summaries = []

        summaries.append(operation_entry)

        # Keep only last 50 operations
        summaries = summaries[-50:]

        with open(summary_file, 'w') as f:
            json.dump(summaries, f, indent=2)

    def get_site_status(self, domain: str) -> Dict:
        """Get comprehensive status for a site from logs"""
        site_dir = self.sites_log_dir / domain

        if not site_dir.exists():
            return {"exists": False}

        status = {"exists": True, "last_operations": [], "error_count": 0, "config_changes": 0}

        # Get last operations
        summary_file = site_dir / "operations_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, 'r') as f:
                    summaries = json.load(f)
                    status["last_operations"] = summaries[-5:]  # Last 5 operations
            except:
                pass

        # Count errors
        error_file = site_dir / "errors.json"
        if error_file.exists():
            try:
                with open(error_file, 'r') as f:
                    errors = json.load(f)
                    status["error_count"] = len(errors)
                    status["last_error"] = errors[-1] if errors else None
            except:
                pass

        # Count config changes
        config_dir = site_dir / "configs"
        if config_dir.exists():
            status["config_changes"] = len(list(config_dir.glob("*.caddy")))

        return status

    def cleanup_old_logs(self, days: int = 30):
        """Cleanup logs older than specified days"""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        cleaned_count = 0
        for log_file in self.log_dir.rglob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                cleaned_count += 1

        self.main_logger.info(f"Cleaned up {cleaned_count} old log files")
        return cleaned_count

    def export_site_logs(self, domain: str, output_file: str) -> bool:
        """Export all logs for a specific site"""
        site_dir = self.sites_log_dir / domain

        if not site_dir.exists():
            return False

        import tarfile

        try:
            with tarfile.open(output_file, 'w:gz') as tar:
                tar.add(site_dir, arcname=domain)

            self.log_site_operation(domain, "export_logs", {"output_file": output_file}, True)
            return True
        except Exception as e:
            self.log_error(domain, "export_logs", str(e))
            return False


# Global logger instance
caddy_logger = CaddyLogger()
