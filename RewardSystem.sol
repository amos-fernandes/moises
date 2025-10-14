pragma solidity ^0.8.0;
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract RewardSystem {
    IERC20 public immutable token;
    mapping(address => uint256) public rewards;

    constructor(address _token) {
        token = IERC20(_token);
    }

    function addReward(address user, uint256 amount) external {
        rewards[user] += amount;
    }

    function claimReward() external {
        uint256 amount = rewards[msg.sender];
        require(amount > 0, "No rewards to claim");
        rewards[msg.sender] = 0;
        require(token.transfer(msg.sender, amount), "Transfer failed");
    }
}