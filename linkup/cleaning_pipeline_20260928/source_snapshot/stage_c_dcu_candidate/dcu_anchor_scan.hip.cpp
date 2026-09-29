#include <hip/hip_runtime.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {
constexpr char MAGIC[8] = {'D','C','U','M','A','S','K','1'};
constexpr uint32_t SOFTWARE_BIT = 20;
constexpr uint32_t AI_BIT = 21;
constexpr uint32_t ALL_MASK = (1u << 22) - 1u;

struct Anchor { char text[28]; uint8_t length; uint8_t bit; };

// Alternatives share a bit. These are necessary literals, not replacements
// for Python regex semantics.
__device__ __constant__ Anchor ANCHORS[] = {
  {"large language model",20,0}, {"llm",3,1}, {"generative ai",13,2},
  {"chatgpt",7,3}, {"gpt",3,3}, {"machine learning",16,4},
  {"deep learning",13,5}, {"neural network",14,6}, {"predictive model",16,7},
  {"computer vision",15,8}, {"natural language processing",27,9}, {"nlp",3,9},
  {"artificial intelligence",23,10}, {"ai",2,10},
  {"microsoft office",16,11}, {"ms office",9,11}, {"excel",5,12},
  {"power bi",8,13}, {"tableau",7,14}, {"salesforce",10,15},
  {"sap",3,16}, {"python",6,17}, {"sql",3,18}, {"java",4,19},
};
constexpr int ANCHOR_COUNT = sizeof(ANCHORS) / sizeof(ANCHORS[0]);

__device__ __constant__ char SOFTWARE_ANCHORS[][12] = {
  "office", "excel", "power", "word", "access", "sheets", "sql", "tableau",
  "sas", "spss", "stata", "python", "java", "javascript", "typescript", "c++",
  "c#", ".net", "ruby", "go", "matlab", "salesforce", "sap", "oracle",
  "workday", "servicenow", "slack", "teams", "zoom", "jira", "confluence",
  "asana", "trello", "github", "gitlab"
};
__device__ __constant__ uint8_t SOFTWARE_LENGTHS[] = {
  6,5,5,4,6,6,3,7,3,4,5,6,4,10,10,3,2,4,4,2,6,10,3,6,7,10,5,5,4,4,10,5,6,6,6
};
constexpr int SOFTWARE_COUNT = sizeof(SOFTWARE_LENGTHS) / sizeof(SOFTWARE_LENGTHS[0]);

__device__ __constant__ char AI_ANCHORS[][11] = {
  "artificial", "machine", "generative", "chatgpt", "openai", "gpt", "claude",
  "gemini", "copilot", "dall", "midjourney"
};
__device__ __constant__ uint8_t AI_LENGTHS[] = {10,7,10,7,6,3,6,6,7,4,10};
constexpr int AI_COUNT = sizeof(AI_LENGTHS) / sizeof(AI_LENGTHS[0]);

__device__ unsigned char ascii_lower(unsigned char value) {
  return value >= 'A' && value <= 'Z' ? value + ('a' - 'A') : value;
}

__device__ bool ascii_word(unsigned char value) {
  return (value >= '0' && value <= '9') || (value >= 'A' && value <= 'Z') ||
         (value >= 'a' && value <= 'z') || value == '_';
}

__device__ bool contains_folded(const unsigned char* bytes, uint64_t begin, uint64_t end,
                                const char* anchor, uint8_t length) {
  if (end - begin < length) return false;
  for (uint64_t pos = begin; pos + length <= end; ++pos) {
    bool equal = true;
    for (uint8_t j = 0; j < length; ++j) {
      if (ascii_lower(bytes[pos + j]) != static_cast<unsigned char>(anchor[j])) {
        equal = false; break;
      }
    }
    if (equal) return true;
  }
  return false;
}

__device__ bool contains_standalone_upper(const unsigned char* bytes, uint64_t begin,
                                          uint64_t end, const char* token, uint8_t length) {
  if (end - begin < length) return false;
  for (uint64_t pos = begin; pos + length <= end; ++pos) {
    bool equal = true;
    for (uint8_t j = 0; j < length; ++j) if (bytes[pos + j] != token[j]) equal = false;
    if (equal && (pos == begin || !ascii_word(bytes[pos - 1])) &&
        (pos + length == end || !ascii_word(bytes[pos + length]))) return true;
  }
  return false;
}

__global__ void scan(const unsigned char* bytes, const uint64_t* offsets,
                     uint32_t* masks, uint32_t count) {
  const uint32_t row = blockIdx.x;
  if (row >= count) return;
  const uint64_t begin = offsets[row], end = offsets[row + 1];

  for (uint64_t pos = begin + threadIdx.x; pos < end; pos += blockDim.x) {
    if (bytes[pos] & 0x80) atomicOr(&masks[row], ALL_MASK);
  }
  for (int item = threadIdx.x; item < ANCHOR_COUNT; item += blockDim.x) {
    const Anchor anchor = ANCHORS[item];
    if (contains_folded(bytes, begin, end, anchor.text, anchor.length))
      atomicOr(&masks[row], 1u << anchor.bit);
  }
  for (int item = threadIdx.x; item < SOFTWARE_COUNT; item += blockDim.x)
    if (contains_folded(bytes, begin, end, SOFTWARE_ANCHORS[item], SOFTWARE_LENGTHS[item]))
      atomicOr(&masks[row], 1u << SOFTWARE_BIT);
  if (threadIdx.x == 0 && contains_standalone_upper(bytes, begin, end, "R", 1))
    atomicOr(&masks[row], 1u << SOFTWARE_BIT);
  for (int item = threadIdx.x; item < AI_COUNT; item += blockDim.x)
    if (contains_folded(bytes, begin, end, AI_ANCHORS[item], AI_LENGTHS[item]))
      atomicOr(&masks[row], 1u << AI_BIT);
  if (threadIdx.x == 0 && contains_standalone_upper(bytes, begin, end, "AI", 2))
    atomicOr(&masks[row], 1u << AI_BIT);
}

void check(hipError_t status, const char* operation) {
  if (status != hipSuccess) {
    std::fprintf(stderr, "%s: %s\n", operation, hipGetErrorString(status));
    std::exit(2);
  }
}

template <typename T> T read_scalar(std::ifstream& input) {
  T value{};
  input.read(reinterpret_cast<char*>(&value), sizeof(value));
  if (!input) { std::fprintf(stderr, "truncated input\n"); std::exit(2); }
  return value;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 3) {
    std::fprintf(stderr, "usage: dcu_anchor_scan INPUT.bin OUTPUT.bin\n");
    return 2;
  }
  std::ifstream input(argv[1], std::ios::binary);
  char magic[8]; input.read(magic, 8);
  if (!input || std::string(magic, 8) != std::string(MAGIC, 8)) {
    std::fprintf(stderr, "invalid input magic\n"); return 2;
  }
  const uint32_t count = read_scalar<uint32_t>(input);
  std::vector<uint64_t> offsets(static_cast<size_t>(count) + 1);
  input.read(reinterpret_cast<char*>(offsets.data()), offsets.size() * sizeof(uint64_t));
  if (!input) { std::fprintf(stderr, "truncated offsets\n"); return 2; }
  if (offsets.front() != 0) { std::fprintf(stderr, "invalid first offset\n"); return 2; }
  for (size_t i = 1; i < offsets.size(); ++i) {
    if (offsets[i] < offsets[i - 1]) { std::fprintf(stderr, "unordered offsets\n"); return 2; }
  }
  std::vector<unsigned char> bytes(offsets.back());
  input.read(reinterpret_cast<char*>(bytes.data()), bytes.size());
  if (static_cast<size_t>(input.gcount()) != bytes.size()) {
    std::fprintf(stderr, "truncated text payload\n"); return 2;
  }

  unsigned char* d_bytes = nullptr; uint64_t* d_offsets = nullptr; uint32_t* d_masks = nullptr;
  check(hipMalloc(&d_bytes, bytes.size() ? bytes.size() : 1), "hipMalloc bytes");
  check(hipMalloc(&d_offsets, offsets.size() * sizeof(uint64_t)), "hipMalloc offsets");
  check(hipMalloc(&d_masks, (count ? count : 1) * sizeof(uint32_t)), "hipMalloc masks");
  if (!bytes.empty()) check(hipMemcpy(d_bytes, bytes.data(), bytes.size(), hipMemcpyHostToDevice), "copy bytes");
  check(hipMemcpy(d_offsets, offsets.data(), offsets.size() * sizeof(uint64_t), hipMemcpyHostToDevice), "copy offsets");
  check(hipMemset(d_masks, 0, count * sizeof(uint32_t)), "clear masks");
  if (count) {
    hipLaunchKernelGGL(scan, dim3(count), dim3(64), 0, 0, d_bytes, d_offsets, d_masks, count);
    check(hipGetLastError(), "launch scan");
  }
  std::vector<uint32_t> masks(count);
  if (count) check(hipMemcpy(masks.data(), d_masks, count * sizeof(uint32_t), hipMemcpyDeviceToHost), "copy masks");
  hipFree(d_masks); hipFree(d_offsets); hipFree(d_bytes);

  std::ofstream output(argv[2], std::ios::binary | std::ios::trunc);
  output.write(MAGIC, 8);
  output.write(reinterpret_cast<const char*>(&count), sizeof(count));
  output.write(reinterpret_cast<const char*>(masks.data()), masks.size() * sizeof(uint32_t));
  if (!output) { std::fprintf(stderr, "failed to write output\n"); return 2; }
  return 0;
}
