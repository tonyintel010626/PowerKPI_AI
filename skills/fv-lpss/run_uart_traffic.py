#!/usr/bin/env python3
"""
LPSS UART Traffic Runner

Runs UART traffic tests using the vjt.lpss module.

Usage:
    python run_uart_traffic.py <port> <size> [options]

Arguments:
    port        UART port number (0-2)
    size        Number of bytes to transfer

Options:
    --dma              Enable DMA mode (default: PIO mode)
    --channel <n>      DMA channel (default: 0)
    --dma-intr         Enable DMA interrupt checking
    --external         Use external loopback (default: internal)
    --speed <baud>     Baud rate (default: 115200)

Examples:
    python run_uart_traffic.py 0 32
    python run_uart_traffic.py 0 32 --dma --channel 0 --dma-intr
    python run_uart_traffic.py 1 1024 --dma --speed 921600
    python run_uart_traffic.py 2 100 --external

VJT LPSS Scripts Location: C:\\pythonsv\\novalake\\vjt\\lpss

Direct PythonSV Usage:
    import sys
    sys.path.insert(0, r'C:\\pythonsv\\novalake')
    import vjt.lpss.lpss_main as lmain
    
    # Run UART0 with 32 bytes, internal loopback
    result = lmain.lhc.ports[0].ioctl(internal=True, size=32, channel=0, dma_intr=True)
    
    # Run UART1 with 1KB, DMA mode
    result = lmain.lhc.ports[1].ioctl(internal=True, size=1024, dma=True, channel=0, dma_intr=True)
"""

import sys
import argparse

# Add VJT package path
sys.path.insert(0, r'C:\pythonsv\novalake')

def run_uart_traffic(port, size, dma=False, channel=0, dma_intr=False, internal=True, speed=115200):
    """
    Run UART traffic test using vjt.lpss module
    
    Args:
        port: UART port number (0-2)
        size: Number of bytes to transfer
        dma: Enable DMA mode (default: False for PIO mode)
        channel: DMA channel number (default: 0)
        dma_intr: Enable DMA interrupt checking (default: False)
        internal: Use internal loopback (default: True)
        speed: Baud rate (default: 115200)
    
    Returns:
        0: Success
        1: TX timeout
        2: RX timeout
        3: DMA timeout
        5: Function disabled
        6: DMA interrupt check failed
    """
    print("=" * 80)
    print("LPSS UART Traffic Runner")
    print("=" * 80)
    print(f"Initializing PythonSV... (this may take ~25 seconds)")
    print()
    
    try:
        # Import vjt.lpss module
        import vjt.lpss.lpss_main as lmain
        
        print(f"✓ PythonSV initialized successfully")
        print()
        print(f"Test Configuration:")
        print(f"  Port:           UART{port}")
        print(f"  Size:           {size} bytes")
        print(f"  Mode:           {'DMA' if dma else 'PIO'}")
        print(f"  Loopback:       {'Internal' if internal else 'External'}")
        print(f"  Speed:          {speed} baud")
        if dma:
            print(f"  DMA Channel:    {channel}")
            print(f"  DMA Interrupt:  {dma_intr}")
        print()
        print("-" * 80)
        
        # Find the UART port
        uart_port = None
        for p in lmain.lhc.ports:
            if hasattr(p, 'protocol') and p.protocol == 'uart' and p.port_number == port:
                uart_port = p
                break
        
        if uart_port is None:
            print(f"✗ Error: UART{port} not found in lpss_hc.ports")
            return -1
        
        print(f"✓ Found UART{port} in lpss_hc.ports")
        print()
        print(f"Running UART traffic test...")
        print("-" * 80)
        
        # Run the traffic test
        result = uart_port.ioctl(
            internal=internal,
            size=size,
            dma=dma,
            channel=channel,
            dma_intr=dma_intr,
            speed=speed
        )
        
        print("-" * 80)
        print()
        
        # Interpret result
        result_msgs = {
            0: "✓ SUCCESS - Traffic test completed successfully",
            1: "✗ FAILED - TX timeout",
            2: "✗ FAILED - RX timeout",
            3: "✗ FAILED - DMA timeout",
            5: "✗ FAILED - Function disabled (check PSF configuration)",
            6: "✗ FAILED - DMA interrupt check failed"
        }
        
        msg = result_msgs.get(result, f"✗ FAILED - Unknown error code: {result}")
        print(msg)
        print()
        
        return result
        
    except Exception as e:
        print(f"✗ Error during UART traffic test:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return -1

def main():
    parser = argparse.ArgumentParser(
        description='Run LPSS UART traffic tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 0 32                              # UART0, 32 bytes, PIO, internal loopback
  %(prog)s 0 32 --dma --channel 0 --dma-intr # UART0, 32 bytes, DMA with interrupt
  %(prog)s 1 1024 --dma                      # UART1, 1KB, DMA mode
  %(prog)s 2 100 --external                  # UART2, 100 bytes, external loopback
        """
    )
    
    parser.add_argument('port', type=int, help='UART port number (0-2)')
    parser.add_argument('size', type=int, help='Number of bytes to transfer')
    parser.add_argument('--dma', action='store_true', help='Enable DMA mode (default: PIO)')
    parser.add_argument('--channel', type=int, default=0, help='DMA channel (default: 0)')
    parser.add_argument('--dma-intr', action='store_true', help='Enable DMA interrupt checking')
    parser.add_argument('--external', action='store_true', help='Use external loopback (default: internal)')
    parser.add_argument('--speed', type=int, default=115200, help='Baud rate (default: 115200)')
    
    args = parser.parse_args()
    
    # Validate port number
    if args.port < 0 or args.port > 2:
        print(f"Error: Invalid port number {args.port}. Valid range: 0-2")
        sys.exit(1)
    
    # Validate size
    if args.size < 1:
        print(f"Error: Size must be at least 1 byte")
        sys.exit(1)
    
    # Run the test
    result = run_uart_traffic(
        port=args.port,
        size=args.size,
        dma=args.dma,
        channel=args.channel,
        dma_intr=args.dma_intr,
        internal=not args.external,
        speed=args.speed
    )
    
    sys.exit(result)

if __name__ == '__main__':
    main()
