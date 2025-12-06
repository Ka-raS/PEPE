pragma solidity ^0.8.0;

contract SimpleStorage {
    string public name = "SimpleStorage";
    string public symbol = "STK";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    
    mapping(address => uint256) public balanceOf;
    address public owner;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Mint(address indexed to, uint256 value);
    event Burn(address indexed from, uint256 value);
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1000000 * 10 ** uint256(decimals);
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    
    // Chuyển token
    function transfer(address _to, uint256 _value) public returns (bool success) {
        require(_to != address(0), "Invalid address");
        require(balanceOf[msg.sender] >= _value, "Insufficient balance");
        
        balanceOf[msg.sender] -= _value;
        balanceOf[_to] += _value;
        
        emit Transfer(msg.sender, _to, _value);
        return true;
    }
    
    // Cộng token (mint) - chỉ owner có thể gọi
    function mint(address _to, uint256 _value) public returns (bool success) {
        require(_to != address(0), "Invalid address");
        require(msg.sender == owner, "Only owner can mint");
        
        totalSupply += _value;
        balanceOf[_to] += _value;
        
        emit Mint(_to, _value);
        emit Transfer(address(0), _to, _value);
        return true;
    }    
    // Trừ token (burn)
    function burn(uint256 _value) public returns (bool success) {
        require(balanceOf[msg.sender] >= _value, "Insufficient balance");
        
        balanceOf[msg.sender] -= _value;
        totalSupply -= _value;
        
        emit Burn(msg.sender, _value);
        emit Transfer(msg.sender, address(0), _value);
        return true;
    }
    
    // Lấy số dư
    function getBalance(address _owner) public view returns (uint256) {
        return balanceOf[_owner];
    }
    
    // Lấy tổng cung
    function getTotalSupply() public view returns (uint256) {
        return totalSupply;
    }
}