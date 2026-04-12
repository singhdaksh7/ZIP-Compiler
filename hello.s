    .section .rodata
.int_fmt:
    .string "%d\n"
.str_fmt:
    .string "%s\n"

    .text
    .globl main
main:
    pushq %rbp
    movq %rsp, %rbp
    subq $32, %rsp
    movq $42, %rax
    movq %rax, -8(%rbp)
    movq $10, %rax
    movq %rax, -16(%rbp)
    movq -8(%rbp), %rax
    pushq %rax
    movq -16(%rbp), %rax
    movq %rax, %rcx
    popq %rax
    addq %rcx, %rax
    movq %rax, -24(%rbp)
    movq -24(%rbp), %rax
    movq %rax, %rsi
    leaq .int_fmt(%rip), %rdi
    movq $0, %rax
    call printf
    movq -24(%rbp), %rax
    pushq %rax
    movq $50, %rax
    movq %rax, %rcx
    popq %rax
    cmpq %rcx, %rax
    setge %al
    movzbq %al, %rax
    cmpq $0, %rax
    je .Lelse_1
    movq $1, %rax
    movq %rax, %rsi
    leaq .int_fmt(%rip), %rdi
    movq $0, %rax
    call printf
    jmp .Lendif_2
.Lelse_1:
    movq $0, %rax
    movq %rax, %rsi
    leaq .int_fmt(%rip), %rdi
    movq $0, %rax
    call printf
.Lendif_2:
    movq $0, %rax
    movq %rax, -32(%rbp)
.Lwhile_3:
    movq -32(%rbp), %rax
    pushq %rax
    movq $5, %rax
    movq %rax, %rcx
    popq %rax
    cmpq %rcx, %rax
    setl %al
    movzbq %al, %rax
    cmpq $0, %rax
    je .Lendwhile_4
    movq -32(%rbp), %rax
    movq %rax, %rsi
    leaq .int_fmt(%rip), %rdi
    movq $0, %rax
    call printf
    movq -32(%rbp), %rax
    pushq %rax
    movq $1, %rax
    movq %rax, %rcx
    popq %rax
    addq %rcx, %rax
    movq %rax, -32(%rbp)
    jmp .Lwhile_3
.Lendwhile_4:
    movq $0, %rax
    leave
    ret
