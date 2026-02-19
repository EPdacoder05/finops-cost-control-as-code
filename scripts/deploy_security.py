#!/usr/bin/env python3
"""
Multi-Repository Security Deployment Tool
Automates copying security modules to target repositories
"""

import argparse
import shutil
from pathlib import Path
import sys


class SecurityDeployer:
    """Deploy security modules to target repositories"""
    
    # Security module groups
    MODULE_GROUPS = {
        "all": [
            "redos_protection.py",
            "input_validator.py",
            "ai_security.py",
            "crypto_utils.py",
            "webhook_validator.py",
            "__init__.py"
        ],
        "ai-era": [
            "ai_security.py",
            "redos_protection.py",
            "__init__.py"
        ],
        "input-validation": [
            "input_validator.py",
            "redos_protection.py",
            "__init__.py"
        ],
        "crypto": [
            "crypto_utils.py",
            "__init__.py"
        ],
        "webhook": [
            "webhook_validator.py",
            "input_validator.py",
            "__init__.py"
        ]
    }
    
    def __init__(self, source_root: Path):
        """Initialize deployer with source repository path"""
        self.source_root = source_root
        self.security_dir = source_root / "security"
        self.tests_dir = source_root / "tests"
        self.docs_dir = source_root / "docs"
        
    def validate_source(self) -> bool:
        """Validate that source repository has all required files"""
        if not self.security_dir.exists():
            print(f"❌ Security directory not found: {self.security_dir}")
            return False
        
        required_files = [
            "redos_protection.py",
            "input_validator.py",
            "ai_security.py",
            "crypto_utils.py",
            "webhook_validator.py"
        ]
        
        for file in required_files:
            if not (self.security_dir / file).exists():
                print(f"❌ Required file not found: {file}")
                return False
        
        print("✅ Source repository validated")
        return True
    
    def deploy(self, target_root: Path, modules: str = "all", include_tests: bool = True, include_docs: bool = True):
        """
        Deploy security modules to target repository
        
        Args:
            target_root: Path to target repository
            modules: Module group to deploy ("all", "ai-era", "input-validation", etc.)
            include_tests: Whether to copy test files
            include_docs: Whether to copy documentation
        """
        print(f"\n🚀 Deploying security modules to {target_root.name}")
        print(f"   Module group: {modules}")
        
        # Create target directories
        target_security = target_root / "security"
        target_tests = target_root / "tests"
        target_docs = target_root / "docs"
        
        target_security.mkdir(parents=True, exist_ok=True)
        
        # Get files to deploy
        files_to_deploy = self.MODULE_GROUPS.get(modules, self.MODULE_GROUPS["all"])
        
        # Copy security modules
        print("\n📦 Copying security modules:")
        for file in files_to_deploy:
            source_file = self.security_dir / file
            target_file = target_security / file
            
            if source_file.exists():
                shutil.copy2(source_file, target_file)
                print(f"   ✅ {file}")
            else:
                print(f"   ⚠️  {file} not found in source")
        
        # Copy tests
        if include_tests and self.tests_dir.exists():
            target_tests.mkdir(parents=True, exist_ok=True)
            test_file = self.tests_dir / "test_security.py"
            if test_file.exists():
                shutil.copy2(test_file, target_tests / "test_security.py")
                print(f"\n🧪 Copied tests: test_security.py")
        
        # Copy documentation
        if include_docs and self.docs_dir.exists():
            target_docs.mkdir(parents=True, exist_ok=True)
            
            docs_to_copy = [
                "SECURITY.md",
                "MULTI_REPO_DEPLOYMENT.md"
            ]
            
            print("\n📚 Copying documentation:")
            for doc in docs_to_copy:
                source_doc = self.docs_dir / doc
                if source_doc.exists():
                    shutil.copy2(source_doc, target_docs / doc)
                    print(f"   ✅ {doc}")
        
        # Copy requirements.txt
        req_file = self.source_root / "requirements.txt"
        if req_file.exists():
            target_req = target_root / "requirements-security.txt"
            shutil.copy2(req_file, target_req)
            print(f"\n📄 Copied requirements-security.txt")
        
        print(f"\n✅ Deployment to {target_root.name} complete!")
        print("\nNext steps:")
        print(f"   1. cd {target_root}")
        print(f"   2. pip install -r requirements-security.txt")
        print(f"   3. python -m pytest tests/test_security.py")
        print(f"   4. Review docs/SECURITY.md for integration examples")
    
    def list_modules(self):
        """List available module groups"""
        print("\n📦 Available module groups:")
        for group, files in self.MODULE_GROUPS.items():
            print(f"\n  {group}:")
            for file in files:
                print(f"    - {file}")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy security modules to target repositories"
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Target repository path (e.g., ../NullPointVector)"
    )
    parser.add_argument(
        "--modules",
        default="all",
        choices=["all", "ai-era", "input-validation", "crypto", "webhook"],
        help="Module group to deploy (default: all)"
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Don't copy test files"
    )
    parser.add_argument(
        "--no-docs",
        action="store_true",
        help="Don't copy documentation"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available module groups"
    )
    parser.add_argument(
        "--source",
        default=".",
        help="Source repository path (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Get source path
    source_root = Path(args.source).resolve()
    deployer = SecurityDeployer(source_root)
    
    # List modules if requested
    if args.list:
        deployer.list_modules()
        return 0
    
    # Validate source
    if not deployer.validate_source():
        return 1
    
    # Check target provided
    if not args.target:
        print("❌ Target repository path required")
        print("\nUsage:")
        print("  python scripts/deploy_security.py ../NullPointVector")
        print("  python scripts/deploy_security.py ../NullPointVector --modules ai-era")
        print("  python scripts/deploy_security.py --list")
        return 1
    
    # Get target path
    target_root = Path(args.target).resolve()
    if not target_root.exists():
        print(f"❌ Target repository not found: {target_root}")
        return 1
    
    # Deploy
    deployer.deploy(
        target_root,
        modules=args.modules,
        include_tests=not args.no_tests,
        include_docs=not args.no_docs
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
