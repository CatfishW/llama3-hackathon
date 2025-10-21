            `                                   ---"""
Test script to verify Racing Game Client setup
Checks all dependencies and connections
"""

import sys
import importlib

def check_import(module_name, package_name=None):
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✓ {package_name or module_name} is installed")
        return True
    except ImportError:
        print(f"✗ {package_name or module_name} is NOT installed")
        return False

def test_mqtt_connection():
    """Test MQTT broker connection"""
    try:
        import paho.mqtt.client as mqtt
        
        client = mqtt.Client(client_id='test-client')
        client.username_pw_set("TangClinic", "Tang123")
        
        connected = False
        
        def on_connect(client, userdata, flags, rc):
            nonlocal connected
            connected = (rc == 0)
        
        client.on_connect = on_connect
        client.connect("47.89.252.2", 1883, 60)
        client.loop_start()
        
        import time
        time.sleep(2)
        
        client.loop_stop()
        client.disconnect()
        
        if connected:
            print("✓ MQTT broker connection successful")
            return True
        else:
            print("✗ MQTT broker connection failed")
            return False
            
    except Exception as e:
        print(f"✗ MQTT connection error: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("Blood Racing Game - Setup Verification")
    print("=" * 60)
    print()
    
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    else:
        print(f"✗ Python version {version.major}.{version.minor} - requires 3.8+")
    print()
    
    print("Checking required packages...")
    all_good = True
    
    # Check PyQt5
    if check_import("PyQt5.QtWidgets", "PyQt5"):
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication([])
            print("  → PyQt5 GUI system working")
            app.quit()
        except Exception as e:
            print(f"  → PyQt5 error: {str(e)}")
            all_good = False
    else:
        all_good = False
    
    # Check paho-mqtt
    if not check_import("paho.mqtt.client", "paho-mqtt"):
        all_good = False
    
    print()
    
    print("Testing MQTT broker connection...")
    mqtt_ok = test_mqtt_connection()
    print()
    
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    if all_good and mqtt_ok:
        print("✓ All checks passed!")
        print()
        print("You're ready to play!")
        print("1. Start the MQTT server: mqtt_deploy_driving_scene4.py")
        print("2. Run the client: python racing_game_client.py")
        print("   or double-click: launch_client.bat")
        return 0
    else:
        print("✗ Some checks failed")
        print()
        if not all_good:
            print("To install missing packages:")
            print("  pip install -r requirements_client.txt")
        if not mqtt_ok:
            print()
            print("MQTT connection issues:")
            print("  - Make sure the MQTT server is running")
            print("  - Check broker address: 47.89.252.2:1883")
            print("  - Verify firewall settings")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        exit_code = 1
    
    print()
    input("Press Enter to exit...")
    sys.exit(exit_code)
