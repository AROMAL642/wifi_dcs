#!/usr/bin/env python3
"""
Module 1: WiFi Node Discovery
Main entry point for the node discovery module
"""

import time
import argparse
from discovery_service import DiscoveryService
from node_info import NodeInfoCollector


def display_banner():
    """Display application banner"""
    print("\n" + "="*70)
    print(" WiFi Distributed Computing - Module 1: Node Discovery")
    print("="*70 + "\n")


def show_local_info():
    """Display local node information"""
    collector = NodeInfoCollector()
    info = collector.collect_all_info()
    
    print("Local Node Information:")
    print("-" * 70)
    print(f"Hostname:      {info.hostname}")
    print(f"IP Address:    {info.ip_address}")
    print(f"MAC Address:   {info.mac_address}")
    print(f"OS:            {info.os_info}")
    print(f"CPU:           {info.cpu_cores} cores @ {info.cpu_freq_mhz:.0f} MHz (Usage: {info.cpu_percent:.1f}%)")
    print(f"RAM:           {info.ram_available_gb:.2f} GB / {info.ram_total_gb:.2f} GB available")
    print(f"Storage:       {info.storage_available_gb:.2f} GB / {info.storage_total_gb:.2f} GB available")
    
    if info.network_bandwidth_mbps:
        print(f"Network:       {info.network_bandwidth_mbps:.0f} Mbps")
    else:
        print(f"Network:       Bandwidth unknown")
    
    print("-" * 70 + "\n")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='WiFi Node Discovery Service - Module 1',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=10,
        help='Scan interval in seconds (default: 10)'
    )
    
    parser.add_argument(
        '--info-only',
        action='store_true',
        help='Display local node info only and exit'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode - minimal output'
    )
    
    args = parser.parse_args()
    
    if not args.quiet:
        display_banner()
        show_local_info()
    
    # If info-only mode, exit after displaying local info
    if args.info_only:
        return
    
    # Start discovery service
    service = DiscoveryService(scan_interval=args.interval)
    
    try:
        service.start()
        
        if not args.quiet:
            print("   Methods: ARP cache, arp-scan, nmap, ICMP ping sweep")
            print("   Press Ctrl+C to stop.\n")
        
        # Main loop - let scanner handle everything
        while True:
            time.sleep(1)
            
            # In quiet mode, periodically print count
            if args.quiet:
                time.sleep(30)
                count = service.get_node_count()
                if count > 0:
                    print(f"Discovered nodes: {count}")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping discovery service...")
        service.stop()
        
        # Final summary
        if not args.quiet:
            print("\nFinal Summary:")
            service.print_all_nodes()
        
        print("✓ Discovery service stopped. Goodbye!\n")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        service.stop()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
