# 昆山、乌镇离线运行约定

同一代码包，两区只改JSON配置中的region、原始文件manifest、records_index、output_dir和来源校验凭据。不得改抽取规则或seed后仍沿用相同输出目录。若乌镇搬过去的文件仍记录华中旧路径，必须重建路径manifest，但保留basename、bytes、SHA回执以核对同一文件。

现有昆山环境：CentOS7 x86_64，glibc2.17，module python/3.8.10，离线runtime_py38（NumPy1.24.4、PyArrow11.0.0）。候选提取器本身仅stdlib，runner另依赖Arrow/NumPy，无外网服务或模型API调用。

乌镇先查看uname -m、getconf GNU_LIBC_VERSION、python版本、Slurm允许的CPU/内存/队列。仅在Python ABI/架构/glibc兼容时复用昆山wheel，否则在华中下载对应wheel/运行时打包并校验，不能直接搬虚拟环境软链接或默认DCU支持CUDA。正式作业中不安装依赖。

代码包需包括prepare_sample.py、requirement_candidates.py、extract_sample.py、测试、配置样例、ANNOTATION_PROTOCOL.md、代码SHA清单及运行说明。未验证的语义候选始终标记unvalidated_candidate。

乌镇原始输入：待转移的1106个完整Description分片、下载回执和manifest；完整Records索引约15.4GB可复用，以便保持完整分母，无需再次从63GB原始Records构建索引。原始Records若已转移可以保留但不重复建立。新onet-taxonomy/remote-tag约20GB、元数据与词典适合一起转移，先检查免费存储预算。

两区均保留source file+row、文本哈希、代码版本、snapshot、region。以后合并紧凑特征时检查跨区JOB_HASH重复/冲突；相同广告不双计，不同广告相同文案只共享抽取结果而不减少广告权重。

32核只是请求值，以Slurm实际分配为准；每进程Arrow设2线程，外层<=16进程。处理64文件pilot后根据实际吞吐决定全量并发。减少进程/增大批量/改数据读取布局都以耗时和内存测量决定，不以空转或高CPU百分比为目的。
