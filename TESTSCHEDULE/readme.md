整体第三版(.v3)
1.前置条件：
我们的case来自公开芯片（ITC02），将芯片按功能分为多个芯粒
对于测试而言，chiplet主要分为memory、基本逻辑芯片、大规模logic core芯片，对其核心功能需要执行的测试分别是：MBIST、scan、LBIST
此外通过DWR封装寄存器 对于大部分chiplet，需要检测其core与外部联通，即INTEST；对于连接在一起的chiplet，还要检测他们的联通，即EXTEST
此外，对于一摞摞chiplet stack，热量会快速传导，因此我们考虑在stack顶端设置instrument用于监测温度（或其他信息），instrument我们可以通过PTAP-STAP-PTAP-STAP路线周期性访问和返回结果（这里作了一个假设，每一组stack温度相同，底部芯片温度是上面stack温度最大的那一个）
上述所有测试任务都需要经历：通过TAP访问待测芯粒并配置配置寄存器，开启并完成测试任务后返回结果这一流程，差别在于
    BIST（包括MBIST、LBIST），在开启以后，会自动执行测试任务，时间根据内部规模和复杂度而定（一般稍长），运行期间可以通过TAP通道访问其他芯粒
    scan是通过触发器扫描链测试组合时序逻辑，主要流程是：数据shiftin、capture、数据shiftout，移入移出可以通过TAP通道或者FPP通道，FPP相当于把一条跑道划分成很多段来传数据，所以会快很多，也带来更多的热量、但是某个scanchain是否有FPP、有几组FPPlane、每条lane速率有多快，都是根据case来决定，规划时只有使用权没有分配权
    INtest和EXtest都是通过DWR寄存器来测试连接好坏，流程与scan相似，IOtest是大多数chiplet有，EXtest根据生成的case决定，也与2.5D、3D、5.5D结构有关
综合上述描述，访问和配置必须通过TAP通路来实现，但是BIST是可以并行（多个BIST也可能并行，BIST时TAP可以访问其他），而数据的传入传出可以通过TAP，也可以通过FPP通道（如果有）
2.输入：
根据标准测试集ITC02，我们将芯片按功能分为多个芯粒组（有相同功能芯粒的复用），一个 chiplet 可以同时有 scan、LBIST、MBIST、INTEST、EXTEST 等多类测试任务；
任务类型应由 case 的 DFT 配置决定，若没有DFT配置，则根据类型决定其具体的任务类型，比如memory，除了IOtest，还有EXtest和BIST。一个芯粒也可能有多个core，所以可能有INtest1和INtest2。
划分芯粒组以后我们要创建case，有2.5D、3D、5.5D三种情况，然后随机组合堆叠形成一个case，EXtest的情况得根据堆叠情况来决定
于是，我们每组case是一系列chiplet的组合、他们的堆叠情况以及一组特定的测试任务表
由于FPP是IEEE1838可选设计，所以每个case可以随机装配FPP给scan/INtest/EXtest用于减少大量测试时间
3.约束：
考虑电热约束
电约束方面：给case整体设定一个合适的阈值，这是一个trade-off的值。需要保证多个任务并行时功率和不会超过它
热约束方面：通过周期读取顶端instrument可以更新stack的温度（考虑通过用spot提取chiplet温度周期性更新来模拟），每一螺的温度若接近这一螺芯粒中温度阈值的最小值，将使用强制扇热措施（比如后续调度窗口中将禁止向该 stack 分配新的并行测试任务，直到温度下降至安全范围内。）（为降低调度求解复杂度，将每个 stack 的温度状态抽象为一个代表性温度，例如该 stack 内所有 die 的最大温度或加权热点温度。该温度由 HotSpot/紧凑热模型周期性更新，用于调度约束判断。）
4.解决算法（贪婪调度）
5.输出：
    1.整体功率时间（P-t）图 
    2.温度时间（T-t）图：按stack分组
    3.表格：多case（多场景下）与baseline（TAP串行、尽可能并行和利用FPP、传统打包分配方法（这个最后看时间复现一下））对比