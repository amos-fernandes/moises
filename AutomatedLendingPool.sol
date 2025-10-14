pragma solidity ^0.8.0;
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./CreditOracle.sol";

contract AutomatedLendingPool {
    IERC20 public immutable token;
    CreditOracle public immutable creditOracle;
    
    struct Loan {
        uint256 amount;
        uint256 interest;
        uint256 dueDate;
    }
    
    mapping(address => Loan) public loans;
    
    constructor(address _token, address _creditOracle) {
        token = IERC20(_token);
        creditOracle = CreditOracle(_creditOracle);
    }
    
    function requestLoan(uint256 amount) external {
        require(loans[msg.sender].amount == 0, "Existing loan must be repaid");
        bytes32 requestId = creditOracle.requestCreditScore(msg.sender);
        // Lógica para processar o empréstimo com base no score de crédito
    }
    
    function repayLoan() external {
        Loan storage loan = loans[msg.sender];
        require(loan.amount > 0, "No active loan");
        uint256 totalDue = loan.amount + loan.interest;
        require(token.transferFrom(msg.sender, address(this), totalDue), "Transfer failed");
        delete loans[msg.sender];
    }
}