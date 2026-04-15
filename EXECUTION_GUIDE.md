# Detailed Execution Guide - Dynamic Host Blocking System

## 📖 Complete Step-by-Step Execution Instructions

This guide provides detailed commands and expected outputs for running and demonstrating your SDN project.

---

## 🔧 Pre-Execution Setup

### 1. Install Dependencies
```bash
# Run installation script
sudo bash install.sh

# OR install manually
sudo apt-get update
sudo apt-get install -y mininet openvswitch-switch python3-pip
pip3 install ryu
```

### 2. Verify Installation
```bash
# Check Mininet
mn --version
# Expected: mininet 2.x.x

# Check Ryu
ryu-manager --version
# Expected: ryu-manager 4.x

# Check Open vSwitch
ovs-vsctl --version
# Expected: ovs-vsctl (Open vSwitch) 2.x.x
```

### 3. Clean Previous Setup (if any)
```bash
# Clean Mininet
sudo mn -c

# Clean Open vSwitch
sudo ovs-vsctl del-br s1 2>/dev/null || true

# Clear logs
sudo rm -f /tmp/blocking_system.log /tmp/blocked_hosts.log
```

---

## 🚀 Execution Procedure

### Phase 1: Start the System

#### Terminal 1 - Ryu Controller
```bash
cd /path/to/project
ryu-manager --observe-links dynamic_blocking_controller.py
```

**Expected Output:**
```
loading app dynamic_blocking_controller.py
loading app ryu.controller.ofp_handler
instantiating app dynamic_blocking_controller.py of DynamicHostBlockingController
instantiating app ryu.controller.ofp_handler of OFPHandler

============================================================
DYNAMIC HOST BLOCKING SYSTEM - INITIALIZED
============================================================
Packet Threshold: 50 packets/10s
Port Scan Threshold: 10 unique ports
============================================================
```

**Status:** Keep this terminal running - it shows real-time controller events

---

#### Terminal 2 - Mininet Topology
```bash
cd /path/to/project
sudo python3 topology.py
```

**Expected Output:**
```
*** Creating Dynamic Host Blocking Network ***
*** Adding controller
*** Adding switch
*** Adding hosts
*** Adding links
*** Starting network
*** Configuring hosts
h1 h2 h3 h4 
*** Starting controller
c0 
*** Starting 1 switches
s1 ...
*** Network Configuration ***
Switch: s1
Hosts:
  h1: 10.0.0.1 (Normal Host)
  h2: 10.0.0.2 (Normal Host)
  h3: 10.0.0.3 (Attacker/Suspicious Host)
  h4: 10.0.0.4 (Normal Host)

Controller: Ryu (localhost:6653)

*** Testing basic connectivity ***
*** Ping: testing ping reachability
h1 -> h2 h3 h4 
h2 -> h1 h3 h4 
h3 -> h1 h2 h4 
h4 -> h1 h2 h3 
*** Results: 0% dropped (12/12 received)

mininet> 
```

**Status:** Mininet CLI is ready for commands

---

#### Terminal 3 - Flow Table Monitor
```bash
# Watch flow tables update in real-time
watch -n 2 'sudo ovs-ofctl -O OpenFlow13 dump-flows s1'
```

**Initial Output:**
```
cookie=0x0, duration=5.123s, table=0, n_packets=12, n_bytes=1176, priority=0 actions=CONTROLLER:65535
```

**Status:** Shows flow table updates every 2 seconds

---

#### Terminal 4 - Log Monitor
```bash
# Monitor controller logs
tail -f /tmp/blocking_system.log
```

**Initial Output:**
```
2025-01-15 10:30:45,123 - Dynamic Host Blocking Controller Started
2025-01-15 10:30:47,456 - Switch connected: DPID 1
2025-01-15 10:30:47,789 - Table-miss rule installed on switch 1
```

**Status:** Shows live log updates

---

### Phase 2: Execute Test Scenarios

#### Test 1: Normal Traffic Flow

**In Mininet CLI (Terminal 2):**
```bash
mininet> h1 ping -c 5 h2
```

**Expected Output:**
```
PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.
64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=0.234 ms
64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=0.156 ms
64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=0.123 ms
64 bytes from 10.0.0.2: icmp_seq=4 ttl=64 time=0.145 ms
64 bytes from 10.0.0.2: icmp_seq=5 ttl=64 time=0.167 ms

--- 10.0.0.2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4089ms
rtt min/avg/max/mdev = 0.123/0.165/0.234/0.039 ms
```

**Terminal 1 (Controller) will show:**
```
[FLOW INSTALLED] Learning flow for h1 -> h2
```

**Terminal 3 (Flow Table) will show:**
```
priority=1,in_port=1,dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00:00:02 idle_timeout=30 actions=output:2
```

---

#### Test 2: Trigger Blocking (Attack Simulation)

**In Mininet CLI (Terminal 2):**
```bash
mininet> h3 ping -c 100 -i 0.01 h1
```

**What happens:**
1. h3 sends 100 pings very rapidly (10ms interval)
2. After ~50 packets, controller detects high rate
3. Blocking rule is installed
4. Remaining packets are dropped

**Expected Partial Output:**
```
PING 10.0.0.1 (10.0.0.1) 56(84) bytes of data.
64 bytes from 10.0.0.1: icmp_seq=1 ttl=64 time=0.234 ms
64 bytes from 10.0.0.1: icmp_seq=2 ttl=64 time=0.156 ms
...
64 bytes from 10.0.0.1: icmp_seq=48 ttl=64 time=0.167 ms
64 bytes from 10.0.0.1: icmp_seq=49 ttl=64 time=0.189 ms
[packets start getting dropped here]

--- 10.0.0.1 ping statistics ---
100 packets transmitted, 52 received, 48% packet loss, time 990ms
```

**Terminal 1 (Controller) will show:**
```
[SUSPICIOUS ACTIVITY DETECTED]
Source IP: 10.0.0.3
Packet Count: 53 packets
Time Window: 9.87 seconds
Threshold Exceeded: 53 > 50

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
[BLOCKING RULE INSTALLED]
Blocked IP: 10.0.0.3
Action: DROP all packets
Priority: 100 (Highest)
Timeout: 300 seconds
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

[DROPPED] Packet from blocked host: 10.0.0.3
[DROPPED] Packet from blocked host: 10.0.0.3
...
```

**Terminal 3 (Flow Table) will show:**
```
priority=100,ip,nw_src=10.0.0.3 hard_timeout=300 actions=drop
priority=1,in_port=3,dl_src=00:00:00:00:00:03 idle_timeout=30 actions=output:1
priority=0 actions=CONTROLLER:65535
```

**Terminal 4 (Logs) will show:**
```
2025-01-15 10:35:23,456 - High traffic rate detected from 10.0.0.3: 53 packets in 9.87s
2025-01-15 10:35:23,458 - BLOCKING RULE INSTALLED: 10.0.0.3
2025-01-15 10:35:23,459 - Dropped packet from blocked host: 10.0.0.3
```

---

#### Test 3: Verify Blocking

**In Mininet CLI (Terminal 2):**
```bash
mininet> h3 ping -c 5 h1
```

**Expected Output:**
```
PING 10.0.0.1 (10.0.0.1) 56(84) bytes of data.

--- 10.0.0.1 ping statistics ---
5 packets transmitted, 0 received, 100% packet loss, time 4095ms
```

**✅ SUCCESS:** h3 is completely blocked!

---

#### Test 4: Verify Other Hosts Still Work

**In Mininet CLI (Terminal 2):**
```bash
mininet> h1 ping -c 5 h2
```

**Expected Output:**
```
--- 10.0.0.2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss
```

```bash
mininet> h2 ping -c 5 h4
```

**Expected Output:**
```
--- 10.0.0.4 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss
```

**✅ SUCCESS:** Normal hosts unaffected!

---

### Phase 3: Performance Measurements

#### Latency Test (Ping)

**Before Blocking:**
```bash
mininet> h1 ping -c 20 h2
```

**Extract statistics:**
```
rtt min/avg/max/mdev = 0.089/0.156/0.234/0.042 ms
```

**After Blocking h3:**
```bash
mininet> h1 ping -c 20 h3
```

**Expected:**
```
100% packet loss (all packets dropped)
```

---

#### Throughput Test (iperf)

**Terminal 2 - Start iperf server on h2:**
```bash
mininet> h2 iperf -s &
```

**Expected:**
```
------------------------------------------------------------
Server listening on TCP port 5001
TCP window size: 85.3 KByte (default)
------------------------------------------------------------
```

**Terminal 2 - Run iperf client from h1:**
```bash
mininet> h1 iperf -c 10.0.0.2 -t 10
```

**Expected Output:**
```
------------------------------------------------------------
Client connecting to 10.0.0.2, TCP port 5001
TCP window size: 85.0 KByte (default)
------------------------------------------------------------
[  3] local 10.0.0.1 port 42356 connected with 10.0.0.2 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0-10.0 sec  4.25 GBytes  3.65 Gbits/sec
```

**Now test from blocked host h3:**
```bash
mininet> h3 iperf -c 10.0.0.2 -t 5
```

**Expected:**
```
connect failed: Connection timed out
```

---

#### Flow Table Statistics

**Command:**
```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

**Sample Output with Analysis:**
```
cookie=0x0, duration=125.456s, table=0, n_packets=87, n_bytes=8526, 
  priority=100, ip, nw_src=10.0.0.3 hard_timeout=300, actions=drop
  ↑ Blocking rule - dropped 87 packets from 10.0.0.3

cookie=0x0, duration=230.789s, table=0, n_packets=45, n_bytes=4410, 
  priority=1, in_port=1, dl_src=00:00:00:00:00:01, dl_dst=00:00:00:00:00:02 
  idle_timeout=30, actions=output:2
  ↑ Learning flow - h1 to h2, 45 packets forwarded

cookie=0x0, duration=456.123s, table=0, n_packets=156, n_bytes=15288, 
  priority=0 actions=CONTROLLER:65535
  ↑ Table-miss - 156 packets sent to controller
```

---

### Phase 4: Advanced Validation

#### Wireshark Capture

**Terminal 5:**
```bash
# Start Wireshark on s1-eth3 (h3's interface)
sudo wireshark -i s1-eth3 -k
```

**Filter:** `icmp`

**Observations:**
1. Before blocking: ICMP Echo Request and Reply both visible
2. After blocking: Only Echo Request visible (Replies dropped)

---

#### Check Logs

**Controller Log:**
```bash
cat /tmp/blocking_system.log
```

**Expected Content:**
```
2025-01-15 10:30:45 - Dynamic Host Blocking Controller Started
2025-01-15 10:30:47 - Switch connected: DPID 1
2025-01-15 10:35:23 - High traffic rate detected from 10.0.0.3
2025-01-15 10:35:23 - BLOCKING RULE INSTALLED: 10.0.0.3
2025-01-15 10:35:24 - Dropped packet from blocked host: 10.0.0.3
```

**Blocked Hosts Log:**
```bash
cat /tmp/blocked_hosts.log
```

**Expected Content:**
```
2025-01-15 10:35:23 - BLOCKED: 10.0.0.3
```

---

## 🎥 Demo Sequence for Evaluation

### Recommended Flow:

1. **Show topology** (Terminal 2)
   ```
   mininet> net
   ```

2. **Explain controller logic** (show code)
   - Point out packet_in handler
   - Explain detection algorithm
   - Show blocking flow installation

3. **Show initial flow rules** (Terminal 3)
   ```
   sudo ovs-ofctl -O OpenFlow13 dump-flows s1
   ```

4. **Demonstrate normal traffic**
   ```
   mininet> h1 ping -c 5 h2
   ```

5. **Trigger attack**
   ```
   mininet> h3 ping -c 100 -i 0.01 h1
   ```

6. **Show blocking in controller** (Terminal 1 output)

7. **Show blocking flow rule** (Terminal 3)
   ```
   priority=100,ip,nw_src=10.0.0.3 actions=drop
   ```

8. **Verify h3 is blocked**
   ```
   mininet> h3 ping -c 5 h1
   ```

9. **Verify others still work**
   ```
   mininet> h1 ping -c 5 h2
   ```

10. **Show logs**
    ```
    cat /tmp/blocked_hosts.log
    tail /tmp/blocking_system.log
    ```

---

## 🔍 Troubleshooting

### Controller doesn't start
```bash
# Check if port 6653 is in use
sudo netstat -tulpn | grep 6653

# Kill existing Ryu processes
sudo pkill -f ryu-manager
```

### Mininet cannot connect to controller
```bash
# Check controller is running
ps aux | grep ryu-manager

# Restart Open vSwitch
sudo /etc/init.d/openvswitch-switch restart

# Clean and retry
sudo mn -c
```

### Flow rules not appearing
```bash
# Check OpenFlow version
sudo ovs-vsctl get bridge s1 protocols

# Should output: ["OpenFlow13"]

# Set if needed
sudo ovs-vsctl set bridge s1 protocols=OpenFlow13
```

### Blocking not working
```bash
# Check logs for errors
tail -f /tmp/blocking_system.log

# Verify flow priority
sudo ovs-ofctl -O OpenFlow13 dump-flows s1 --sort=priority

# Blocking flow should be priority=100 (highest)
```

---

## 📊 Performance Data to Record

### Metrics Table:

| Metric | Before Blocking | After Blocking |
|--------|----------------|----------------|
| Ping Success (h1→h2) | 100% | 100% |
| Ping Success (h3→h1) | 100% | 0% |
| Avg Latency (h1→h2) | ~0.15ms | ~0.15ms |
| Throughput (h1→h2) | ~3.5Gbps | ~3.5Gbps |
| Flow Table Size | 2 rules | 3 rules |
| Dropped Packets (h3) | 0 | 87+ |

---

## ✅ Final Checklist Before Demo

- [ ] All dependencies installed
- [ ] Controller code tested
- [ ] Topology loads successfully
- [ ] Flow tables visible
- [ ] Blocking works
- [ ] Logs are generated
- [ ] README is complete
- [ ] Code is commented
- [ ] GitHub repo is ready

---

**Good luck with your demonstration! 🎉**
