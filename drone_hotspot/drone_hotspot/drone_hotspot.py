import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from mavros_msgs.srv import CommandBool, SetMode
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import math
import time

class DroneController(Node):
    def __init__(self):
        super().__init__('drone_controller')
        self.get_logger().info("Drone controller node initialized.")
        self.qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        
        self.rate = self.create_rate(20.0) 
        self.pose_publisher = self.create_publisher(PoseStamped, 'mavros/setpoint_position/local', self.qos_profile)
        self.arming_client = self.create_client(CommandBool, 'mavros/cmd/arming')
        self.set_mode_client = self.create_client(SetMode, 'mavros/set_mode')
        self.curr_pos = {'x': 0.0, 'y': 0.0, 'z': 0.0}

    def wait_for_services(self):
        for client in [self.arming_client, self.set_mode_client]:
            if not client.wait_for_service(timeout_sec=5.0):
                self.get_logger().fatal(f'Service {client.srv_name} not available.')
                return False
        return True

    def set_drone_mode(self, mode):
        req = SetMode.Request(custom_mode=mode)
        future = self.set_mode_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result() is not None and future.result().mode_sent

    def arm_drone(self, arm=True):
        req = CommandBool.Request(value=arm)
        future = self.arming_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result() is not None and future.result().success

    def publish_pose(self, x, y, z, yaw=0.0):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = x, y, z
        msg.pose.orientation.z = math.sin(yaw * 0.5)
        msg.pose.orientation.w = math.cos(yaw * 0.5)
        self.pose_publisher.publish(msg)

    def move_to(self, tx, ty, tz, duration_steps=200):
        sx, sy, sz = self.curr_pos['x'], self.curr_pos['y'], self.curr_pos['z']
        
        for i in range(duration_steps + 1):
            t = i / duration_steps
            cmd_x = sx + (tx - sx) * t
            cmd_y = sy + (ty - sy) * t
            cmd_z = sz + (tz - sz) * t
            
            self.publish_pose(cmd_x, cmd_y, cmd_z)
            rclpy.spin_once(self)
            time.sleep(0.05)  
            if not rclpy.ok(): 
                return

        self.curr_pos.update({'x': tx, 'y': ty, 'z': tz})

    def run(self):
        if not self.wait_for_services(): 
            return
        for _ in range(100):
            self.publish_pose(0.0, 0.0, 0.0)
            rclpy.spin_once(self)
            time.sleep(0.05)
            

        if not (self.set_drone_mode('OFFBOARD') and self.arm_drone(True)):
            self.get_logger().error("Failed to arm or set OFFBOARD mode.")
            return

       
        base_alt = 5.0
        hotspots = [(2.0, -1.0), (0.0, 4.0), (5.0, 1.0)]

        
        self.get_logger().info("Taking off...")
        self.move_to(0.0, 0.0, base_alt)

       
        for h_x, h_y in hotspots:
            self.get_logger().info(f"Moving to hotspot: ({h_x}, {h_y})")
            self.move_to(h_x, h_y, base_alt)    
            self.move_to(h_x, h_y, 0.0)         
            self.get_logger().info("Inspection complete.")
            self.move_to(h_x, h_y, base_alt)    

        self.get_logger().info("Returning to home...")
        self.move_to(0.0, 0.0, base_alt)
        self.move_to(0.0, 0.0, 0.0)
        
        self.arm_drone(False)
        self.set_drone_mode('MANUAL')
        self.get_logger().info("Mission successful.")

def main(args=None):
    rclpy.init(args=args)
    node = DroneController()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()