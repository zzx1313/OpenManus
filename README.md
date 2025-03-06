# OpenManus 🙋
Manus is incredible, but OpenManus can achieve any ideas without an Invite Code 🛫!

Our team members @mannaandpoem @XiangJinyu @MoshiQAQ @didiforgithub from @MetaGPT built it within 3 hours!

It's a simple implementation, so we welcome any suggestions, contributions, and feedback!

Enjoy your own agent with OpenManus!

## Installation

1. Create a new conda environment:

```bash
conda create -n open_manus python=3.12
conda activate open_manus
```

2. Clone the repository:

```bash
git clone https://github.com/mannaandpoem/OpenManus.git
cd OpenManus
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

OpenManus requires configuration for the LLM APIs it uses. Follow these steps to set up your configuration:

1. Create a `config.toml` file in the `config` directory (you can copy from the example):

```bash
cp config/config.example.toml config/config.toml
```

2. Edit `config/config.toml` to add your API keys and customize settings:

```toml
# Global LLM configuration
[llm]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Replace with your actual API key
max_tokens = 4096
temperature = 0.0

# Optional configuration for specific LLM models
[llm.vision]
model = "gpt-4o"
base_url = "https://api.openai.com/v1"
api_key = "sk-..."  # Replace with your actual API key
```

## Quick Start
One line for run OpenManus:  

```bash
python main.py
```

Then input your idea via terminal!

## How to contribute 
We welcome any friendly suggestions and helpful contributions! Just create issues or submit pull requests.

Or contact @mannaandpoem via 📧email: mannaandpoem@gmail.com

## Roadmap
- [ ] Better Planning
- [ ] Live Demos
- [ ] Replay
- [ ] RL Fine-tuned Models
- [ ] Comprehensive Benchmarks

## Acknowledgement

Thanks to [broswer use](https://github.com/browser-use/browser-use) for providing basic support for this project!

OpenManus is built by contributors from MetaGPT. Huge thanks to this agent community!